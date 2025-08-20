"""
main.py

Main application script for PagodaLightPico with async architecture.

Controls multiple LED lighting PWM outputs based on individual configurable time windows
and dynamically calculated sunrise and sunset times from sun_times module (JSON-backed with fallback).

The "day" time window start and end times are set dynamically each check
based on the current date's sunrise and sunset times.

Configuration is now managed via JSON files (config.json) with runtime updates
supported through a web interface accessible when WiFi is connected.

The script reads real-time clock (RTC) time using rtc_module and sets PWM
on multiple assigned GPIO pins according to their individual schedules.

Logging is done via simple_logger with timestamps and levels.

Web Interface:
- When WiFi is connected, access http://[pico-ip]/ for configuration management
- All settings can be updated in real-time without restarting the system
- Changes are validated and applied immediately

Async Architecture:
- Web server runs in its own async task
- PWM updates run in a separate async task
- Network monitoring runs in a separate async task
- All tasks run concurrently without blocking each other
"""

import asyncio
import gc
from lib import config_manager as config
from lib import sun_times
import rtc_module
from simple_logger import Logger
from lib.wifi_connect import connect_wifi, sync_time_ntp
import time
from lib.pwm_control import multi_pwm
from lib.web_server import web_server
from lib.mqtt_notifier import mqtt_notifier
from lib.system_status import system_status

log = Logger()

log.info("Starting async system")

# Initialize WiFi and services
wifi_connected = connect_wifi()
if wifi_connected:
    log.info("WiFi connected successfully")
    system_status.set_connection_status(wifi=True)
    
    # Sync time from NTP
    try:
        sync_time_ntp()
        log.info("Time synchronized from NTP")
    except Exception as e:
        log.error(f"NTP sync failed: {e}")
    
    # Web server will be started in the async main() function
    
    # Connect MQTT if enabled
    if mqtt_notifier.connect():
        log.info("MQTT connected successfully")
        system_status.set_connection_status(mqtt=True)
    else:
        log.info("MQTT connection failed or disabled")
        system_status.set_connection_status(mqtt=False)
        
else:
    log.warn("Using RTC time due to WiFi connection failure")
    system_status.set_connection_status(wifi=False, web_server=False, mqtt=False)

# Initialize PWM controller (already initialized in constructor)
# multi_pwm is ready to use

def get_current_window_for_pin(pin_config):
    """
    Determine which time window is currently active for a specific pin.
    
    Args:
        pin_config (dict): Pin configuration with time_windows
        
    Returns:
        tuple: (window_name, window_config) or (None, None) if no active window
    """
    try:
        current_time = rtc_module.get_current_time()
        current_hour = current_time[3]
        current_minute = current_time[4]
        current_minutes_since_midnight = current_hour * 60 + current_minute
        
        time_windows = pin_config.get('time_windows', {})
        
        # Handle dynamic day window with sunrise/sunset
        if 'day' in time_windows:
            day_window = time_windows['day'].copy()
            try:
                # Get current month and day for sunrise/sunset lookup
                current_month = current_time[1]  # Month from RTC time tuple
                current_day = current_time[2]    # Day from RTC time tuple
                sunrise_sunset_data = sun_times.get_sunrise_sunset(current_month, current_day)
                
                # Extract sunrise and sunset times (format: (sunrise_hour, sunrise_min, sunset_hour, sunset_min))
                sunrise_time = (sunrise_sunset_data[0], sunrise_sunset_data[1])
                sunset_time = (sunrise_sunset_data[2], sunrise_sunset_data[3])
                
                day_window['start'] = f"{sunrise_time[0]:02d}:{sunrise_time[1]:02d}"
                day_window['end'] = f"{sunset_time[0]:02d}:{sunset_time[1]:02d}"
                time_windows['day'] = day_window
            except Exception as e:
                log.error(f"Error getting sunrise/sunset times: {e}")
        
        # Check each time window to see if current time falls within it
        for window_name, window_config in time_windows.items():
            if not isinstance(window_config, dict):
                continue
                
            start_str = window_config.get('start')
            end_str = window_config.get('end')
            
            if not start_str or not end_str:
                continue
            
            try:
                start_parts = start_str.split(':')
                end_parts = end_str.split(':')
                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
                
                # Handle overnight windows (e.g., 22:00 to 06:00)
                if start_minutes > end_minutes:
                    if current_minutes_since_midnight >= start_minutes or current_minutes_since_midnight < end_minutes:
                        return window_name, window_config
                else:
                    if start_minutes <= current_minutes_since_midnight < end_minutes:
                        return window_name, window_config
                        
            except (ValueError, IndexError) as e:
                log.error(f"Invalid time format in window {window_name}: {e}")
                continue
        
        return None, None
        
    except Exception as e:
        log.error(f"Error determining current window: {e}")
        return None, None

async def update_pwm_pins():
    """
    Async task to update PWM pins based on current time windows.
    """
    try:
        config_data = config.config_manager.get_config_dict()
        pwm_pins = config_data.get('pwm_pins', {})
        
        pin_updates = {}
        
        for pin_key, pin_config in pwm_pins.items():
            if pin_key.startswith('_'):
                continue  # Skip comment entries
            
            if not isinstance(pin_config, dict):
                log.error(f"Invalid pin config for {pin_key}: expected dict, got {type(pin_config)}")
                continue
            
            enabled = pin_config.get('enabled', False)
            if not enabled:
                continue
            
            gpio_pin = pin_config.get('gpio_pin')
            if gpio_pin is None:
                log.error(f"No GPIO pin specified for {pin_key}")
                continue
            
            # Get current active window
            window_name, window_config = get_current_window_for_pin(pin_config)
            
            if window_config:
                duty_cycle = window_config.get('duty_cycle', 0)
                pin_name = pin_config.get('name', f'Pin {gpio_pin}')
                
                # Update PWM using pin_key instead of gpio_pin
                multi_pwm.set_pin_duty_percent(pin_key, duty_cycle)
                
                # Store update info for notifications
                pin_updates[pin_key] = {
                    'name': pin_name,
                    'window': window_name,
                    'duty_cycle': duty_cycle,
                    'window_start': window_config.get('start'),
                    'window_end': window_config.get('end')
                }
        
        # Update system status with pin information
        if pin_updates:
            system_status.update_multi_pin_status(pin_updates)
            active_pins = sum(1 for update in pin_updates.values() if update.get('duty_cycle', 0) > 0)
            log.debug(f"[PWM_UPDATE] Updated {len(pin_updates)} pins, {active_pins} active")
            
            if mqtt_notifier.connected:
                mqtt_notifier.notify_multi_pin_changes(pin_updates)
        else:
            log.debug("[PWM_UPDATE] No pin updates needed")
            
    except Exception as e:
        error_msg = f"Error updating PWM pins: {e}"
        log.error(error_msg)
        if mqtt_notifier.connected:
            mqtt_notifier.notify_error(error_msg)

async def pwm_update_task():
    """
    Async task that periodically updates PWM pins based on configured update_interval.
    """
    update_interval = config.UPDATE_INTERVAL
    log.info(f"[PWM_TASK] Starting PWM update task with {update_interval}s interval")
    
    while True:
        try:
            log.debug(f"[PWM_TASK] Performing PWM update (interval: {update_interval}s)")
            await update_pwm_pins()
            await asyncio.sleep(update_interval)
        except Exception as e:
            log.error(f"[PWM_TASK] Error in PWM update task: {e}")
            await asyncio.sleep(update_interval)

async def network_monitor_task():
    """
    Async task that monitors network connectivity and handles reconnections.
    """
    last_network_check = 0
    network_check_interval = config.NETWORK_CHECK_INTERVAL  # seconds
    
    log.info(f"[NETWORK_TASK] Starting network monitor task with {network_check_interval}s interval")
    
    while True:
        try:
            current_time = time.time()
            elapsed = current_time - last_network_check
            
            # Periodic network health check
            if elapsed >= network_check_interval:
                try:
                    import network
                    wlan = network.WLAN(network.STA_IF)
                    if not wlan.isconnected():
                        log.warn("[NETWORK] WiFi connection lost, attempting reconnection...")
                        system_status.set_connection_status(wifi=False, web_server=False, mqtt=False)
                        # Try to reconnect
                        if connect_wifi():
                            log.info("[NETWORK] WiFi reconnected successfully")
                            system_status.set_connection_status(wifi=True)
                            # Restart web server if needed
                            if not web_server.running:
                                if await web_server.start():
                                    system_status.set_connection_status(web_server=True)
                                    log.info("[NETWORK] Web server restarted successfully")
                                else:
                                    log.error("[NETWORK] Failed to restart web server")
                            # Reconnect MQTT if needed
                            if not mqtt_notifier.connected:
                                if mqtt_notifier.connect():
                                    system_status.set_connection_status(mqtt=True)
                    else:
                        # Check MQTT connection health
                        if mqtt_notifier.notifications_enabled and not mqtt_notifier.connected:
                            log.debug("[NETWORK] MQTT disconnected, attempting reconnection...")
                            if mqtt_notifier.connect():
                                system_status.set_connection_status(mqtt=True)
                                log.info("[NETWORK] MQTT reconnected successfully")
                    
                    last_network_check = current_time
                except Exception as e:
                    log.error(f"[NETWORK] Network health check error: {e}")
                    last_network_check = current_time
            
            # Sleep until the next check window (clamped to avoid very long sleeps)
            now = time.time()
            remaining = network_check_interval - (now - last_network_check)
            # Clamp between 0.5s and 5s to remain responsive to cancellations/errors
            sleep_time = 5.0 if remaining > 5.0 else (0.5 if remaining < 0.5 else remaining)
            await asyncio.sleep(sleep_time)
            
        except Exception as e:
            log.error(f"Error in network monitor task: {e}")
            await asyncio.sleep(5)  # Wait before retrying

async def ram_telemetry_task():
    """
    Periodically log RAM usage if enabled in config.
    """
    interval = config.RAM_TELEMETRY_INTERVAL
    log.info(f"[RAM] Telemetry task started with {interval}s interval")
    while True:
        try:
            gc.collect()
            free = gc.mem_free()
            alloc = gc.mem_alloc() if hasattr(gc, 'mem_alloc') else None
            if alloc is not None:
                log.info(f"[RAM] free={free} bytes, alloc={alloc} bytes")
            else:
                log.info(f"[RAM] free={free} bytes")
        except Exception as e:
            log.error(f"[RAM] Telemetry error: {e}")
        await asyncio.sleep(interval)

async def main():
    """
    Main async function that starts all tasks.
    """
    log.info("Starting async main loop")
    
    # Start web server if WiFi is connected
    if wifi_connected:
        log.info("[MAIN] Starting async web server...")
        server_started = await web_server.start()
        if server_started:
            log.info("[MAIN] Async web server started successfully")
            system_status.set_connection_status(web_server=True)
        else:
            log.error("[MAIN] Failed to start async web server")
            system_status.set_connection_status(web_server=False)
    
    # Create and start all async tasks
    tasks = []
    
    # PWM update task
    tasks.append(asyncio.create_task(pwm_update_task()))
    
    # Network monitoring task
    tasks.append(asyncio.create_task(network_monitor_task()))
    
    # Web server task (if WiFi connected and server started)
    if wifi_connected and web_server.running:
        log.info("[MAIN] Adding web server task to async loop")
        tasks.append(asyncio.create_task(web_server.serve_forever()))
    
    # Optional RAM telemetry task
    if config.RAM_TELEMETRY_ENABLED:
        tasks.append(asyncio.create_task(ram_telemetry_task()))
    
    log.info(f"Started {len(tasks)} async tasks")
    
    try:
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        log.error(f"Error in main async loop: {e}")
    finally:
        # Cleanup
        if wifi_connected:
            web_server.stop()
        log.info("System shutdown complete")

if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("System interrupted by user")
    except Exception as e:
        log.error(f"Fatal error: {e}")
    finally:
        log.info("System exit")