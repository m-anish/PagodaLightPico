"""
main.py

Main application script for PagodaLightPico.

Controls multiple LED lighting PWM outputs based on individual configurable time windows
and dynamically calculated sunrise and sunset times from sun_times_leh module.

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
"""

from lib import config_manager as config
import sun_times_leh
import rtc_module
from simple_logger import Logger
from wifi_connect import connect_wifi, sync_time_ntp
import time
from lib.pwm_control import multi_pwm
from lib.web_server import web_server
from lib.mqtt_notifier import mqtt_notifier
from lib.system_status import system_status

log = Logger()

log.info("Starting system")

wifi_connected = connect_wifi()
if wifi_connected:
    log.info("WiFi connected successfully")
    system_status.set_connection_status(wifi=True)
    
    if not sync_time_ntp():
        log.warn("Using RTC time due to NTP sync failure")
    
    # Start web server for configuration management
    if web_server.start():
        # Get actual IP address for the log message
        try:
            import network
            wlan = network.WLAN(network.STA_IF)
            if wlan.isconnected():
                ip_address = wlan.ifconfig()[0]
                log.info(f"Web configuration server started - access via http://{ip_address}/")
            else:
                log.info("Web configuration server started - access via http://[pico-ip]/")
        except Exception as e:
            log.info("Web configuration server started - access via http://[pico-ip]/")
            log.debug(f"Could not get IP address: {e}")
        
        system_status.set_connection_status(web_server=True)
        
        # Device accessible via configured hostname or direct IP
        hostname = config.config_manager.get_config_dict().get('hostname', 'PagodaLightPico')
        log.info(f"Device hostname: {hostname}")
    else:
        log.error("Failed to start web configuration server")
        system_status.set_connection_status(web_server=False)
    
    # Start MQTT notifications if enabled
    if mqtt_notifier.connect():
        log.info("MQTT notifications enabled")
        system_status.set_connection_status(mqtt=True)
    else:
        log.warn("MQTT notifications not available")
        system_status.set_connection_status(mqtt=False)
else:
    log.warn("Using RTC time due to WiFi connection failure")
    system_status.set_connection_status(wifi=False, web_server=False, mqtt=False)


def time_str_to_minutes(time_str):
    """
    Convert a time string 'HH:MM' into total minutes past midnight.

    Args:
        time_str (str): Time formatted as 'HH:MM'.

    Returns:
        int: Total minutes past midnight.
    """
    hour, minute = map(int, time_str.split(":"))
    return hour * 60 + minute


def int_to_time_str(hour, minute):
    """
    Format integers hour and minute as zero-padded 'HH:MM' string.

    Args:
        hour (int): Hour component (0-23).
        minute (int): Minute component (0-59).

    Returns:
        str: Time string formatted as 'HH:MM'.
    """
    return f"{hour:02d}:{minute:02d}"


def get_current_window(time_windows, current_time_tuple):
    """
    Determine the currently active time window and corresponding PWM duty
    cycle.

    The "day" window's start and end times are dynamically updated from
    sunrise and sunset times retrieved via sun_times_leh.get_sunrise_sunset().

    Args:
        time_windows (dict): Dictionary of time windows with start/end times
            and duty cycles.
        current_time_tuple (tuple): Current local time tuple (year, month,
            day, hour, minute, ...).

    Returns:
        tuple (str, int): The active window name and duty cycle percentage.
                         Returns (None, 0) if no active window matches.
    """
    current_minutes = current_time_tuple[3] * 60 + current_time_tuple[4]
    month = current_time_tuple[1]
    day = current_time_tuple[2]

    # Reduce debug logging to save memory
    # log.debug(f"[MAIN] RTC current time: {current_time_tuple}")
    sunrise_h, sunrise_m, sunset_h, sunset_m = \
        sun_times_leh.get_sunrise_sunset(month, day)
    # log.debug(f"[MAIN] Sunrise/sunset times for {month}/{day}: "
    #           f"{sunrise_h:02d}:{sunrise_m:02d}, "
    #           f"{sunset_h:02d}:{sunset_m:02d}")

    sunrise_str = int_to_time_str(sunrise_h, sunrise_m)
    sunset_str = int_to_time_str(sunset_h, sunset_m)
    # log.debug(f"[MAIN] Formatted sunrise/sunset times: {sunrise_str}, {sunset_str}")

    windows = dict(time_windows)
    if "day" in windows:
        windows["day"] = windows["day"].copy()
        windows["day"]["start"] = sunrise_str
        windows["day"]["end"] = sunset_str

    for window_name, window in windows.items():
        start = time_str_to_minutes(window["start"])
        end = time_str_to_minutes(window["end"])
        duty = window["duty_cycle"]

        # log.debug(f"[MAIN] Checking window '{window_name}' start: {window['start']} "
        #           f"({start}), end: {window['end']} ({end}), duty: {duty}")

        if start <= end:
            if start <= current_minutes < end:
                # log.debug(f"[MAIN] Current time {current_minutes} is within window "
                #           f"'{window_name}'")
                return window_name, duty
        else:
            # Handle overnight windows crossing midnight
            if current_minutes >= start or current_minutes < end:
                # log.debug(
                #     f"[MAIN] Current time {current_minutes} is within overnight "
                #     f"window '{window_name}'")
                return window_name, duty
    # log.debug("[MAIN] No matching time window found")
    return None, 0


def update_pwm_pins():
    """
    Reads the current time from RTC and updates all enabled PWM pin duty cycles
    based on their individual time windows. Also updates system status and sends
    MQTT notifications when windows change.
    """
    try:
        current_time_tuple = rtc_module.get_current_time()
        config_dict = config.config_manager.get_config_dict()
        pwm_pins = config_dict.get('pwm_pins', {})
        
        # Process each enabled PWM pin
        pin_updates = {}
        for pin_key, pin_config in pwm_pins.items():
            # Skip comment fields and disabled pins
            if pin_key.startswith('_') or not pin_config.get('enabled', False):
                continue
                
            pin_name = pin_config.get('name', pin_key)
            time_windows = pin_config.get('time_windows', {})
            
            # Get current window for this pin
            window, duty_cycle = get_current_window(time_windows, current_time_tuple)
            
            # Get window start/end times for status and notifications
            window_start = None
            window_end = None
            if window and window in time_windows:
                window_config = time_windows[window]
                window_start = window_config.get("start")
                window_end = window_config.get("end")
                
                # For day window, use actual sunrise/sunset times
                if window == "day":
                    month = current_time_tuple[1]
                    day = current_time_tuple[2]
                    sunrise_h, sunrise_m, sunset_h, sunset_m = sun_times_leh.get_sunrise_sunset(month, day)
                    window_start = int_to_time_str(sunrise_h, sunrise_m)
                    window_end = int_to_time_str(sunset_h, sunset_m)
            
            # Update PWM for this pin
            if window:
                # Reduce debug logging to save memory
                # log.info(f"Pin {pin_name}: Active window '{window}', setting duty cycle: {duty_cycle}%")
                multi_pwm.set_pin_duty_percent(pin_key, duty_cycle)
            else:
                # log.warn(f"Pin {pin_name}: No active window detected, turning off")
                multi_pwm.set_pin_duty_percent(pin_key, 0)
                duty_cycle = 0
            
            # Store pin update info for status and notifications
            pin_updates[pin_key] = {
                'name': pin_name,
                'window': window,
                'duty_cycle': duty_cycle,
                'window_start': window_start,
                'window_end': window_end
            }
        
        # Update system status with all pin information
        system_status.update_multi_pin_status(pin_updates)
        
        # Send MQTT notifications for changed windows
        mqtt_notifier.notify_multi_pin_changes(pin_updates)
            
    except Exception as e:
        error_msg = f"Error updating PWM pins: {e}"
        log.error(error_msg)
        
        # Record error in system status
        system_status.record_error(error_msg)
        
        # Send error notification
        mqtt_notifier.notify_error(error_msg)
        
        # Turn off all pins in case of error
        try:
            multi_pwm.set_all_pins_duty_percent(0)
            system_status.update_multi_pin_status({})
        except Exception as cleanup_error:
            log.error(f"Error during cleanup: {cleanup_error}")


def main_loop():
    """
    Main loop that repeatedly updates all PWM pins and handles web requests.
    
    The loop now integrates web server request handling with multi-pin PWM updates,
    and supports runtime configuration reloading when updates are received
    via the web interface.
    """
    last_pwm_update = 0
    web_request_interval = 0.1  # Handle web requests every 100ms
    
    while True:
        try:
            current_time = time.time()
            
            # Handle web requests frequently (non-blocking)
            if web_server.running:
                web_server.handle_requests(timeout=web_request_interval)
            
            # Update PWM pins based on configured interval
            if current_time - last_pwm_update >= config.UPDATE_INTERVAL:
                # Check if configuration was updated via web interface
                current_config = config.config_manager.get_config_dict()
                if hasattr(config.config_manager, '_last_config_hash'):
                    import json
                    current_hash = hash(json.dumps(current_config))
                    if current_hash != config.config_manager._last_config_hash:
                        # Reduce debug logging to save memory
                        # log.info("Configuration change detected, reloading...")
                        config.config_manager.reload()
                        # Re-initialize multi-PWM manager with new configuration
                        multi_pwm.reload_config()
                        config.config_manager._last_config_hash = current_hash
                else:
                    # Initialize hash tracking
                    import json
                    config.config_manager._last_config_hash = hash(json.dumps(current_config))
                
                update_pwm_pins()
                last_pwm_update = current_time
            else:
                # Short sleep to prevent excessive CPU usage
                time.sleep(web_request_interval)
                
        except KeyboardInterrupt:
            log.info("Shutdown requested")
            if web_server.running:
                web_server.stop()
            # Clean up PWM controllers
            try:
                multi_pwm.deinit_all()
            except Exception as cleanup_error:
                log.error(f"Error during PWM cleanup: {cleanup_error}")
            break
        except Exception as e:
            log.error(f"Error in main loop: {e}")
            time.sleep(1)  # Brief pause on error


# Start the main loop automatically when the module is loaded
main_loop()

