"""
main.py

Main application script for PagodaLightPico.

Controls LED lighting PWM duty cycle based on configurable time windows
and dynamically calculated sunrise and sunset times from sun_times_leh module.

The "day" time window start and end times are set dynamically each check
based on the current date's sunrise and sunset times.

Configuration is now managed via JSON files (config.json) with runtime updates
supported through a web interface accessible when WiFi is connected.

The script reads real-time clock (RTC) time using rtc_module and sets PWM
on an assigned GPIO pin accordingly.

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
from lib.pwm_control import PWMController
from lib.web_server import web_server
from lib.mqtt_notifier import mqtt_notifier
from lib.system_status import system_status

log = Logger()

# Initialize PWM controller
led_pwm = PWMController(freq=config.PWM_FREQUENCY, pin=config.LED_PWM_PIN)

log.info("Starting system")

wifi_connected = connect_wifi()
if wifi_connected:
    log.info("WiFi connected successfully")
    system_status.set_connection_status(wifi=True)
    
    if not sync_time_ntp():
        log.warn("Using RTC time due to NTP sync failure")
    
    # Start web server for configuration management
    if web_server.start():
        log.info("Web configuration server started - access via http://[pico-ip]/")
        system_status.set_connection_status(web_server=True)
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

    log.debug(f"RTC current time: {current_time_tuple}")
    sunrise_h, sunrise_m, sunset_h, sunset_m = \
        sun_times_leh.get_sunrise_sunset(month, day)
    log.debug(f"Sunrise/sunset times for {month}/{day}: "
              f"{sunrise_h:02d}:{sunrise_m:02d}, "
              f"{sunset_h:02d}:{sunset_m:02d}")

    sunrise_str = int_to_time_str(sunrise_h, sunrise_m)
    sunset_str = int_to_time_str(sunset_h, sunset_m)
    log.debug(f"Formatted sunrise/sunset times: {sunrise_str}, {sunset_str}")

    windows = dict(time_windows)
    if "day" in windows:
        windows["day"] = windows["day"].copy()
        windows["day"]["start"] = sunrise_str
        windows["day"]["end"] = sunset_str

    for window_name, window in windows.items():
        start = time_str_to_minutes(window["start"])
        end = time_str_to_minutes(window["end"])
        duty = window["duty_cycle"]

        log.debug(f"Checking window '{window_name}' start: {window['start']} "
                  f"({start}), end: {window['end']} ({end}), duty: {duty}")

        if start <= end:
            if start <= current_minutes < end:
                log.debug(f"Current time {current_minutes} is within window "
                          f"'{window_name}'")
                return window_name, duty
        else:
            # Handle overnight windows crossing midnight
            if current_minutes >= start or current_minutes < end:
                log.debug(
                    f"Current time {current_minutes} is within overnight "
                    f"window '{window_name}'")
                return window_name, duty
    log.debug("No matching time window found")
    return None, 0


def update_led():
    """
    Reads the current time from RTC and updates the LED PWM duty cycle
    based on the active time window. Also updates system status and sends
    MQTT notifications when windows change.
    """
    try:
        current_time_tuple = rtc_module.get_current_time()
        window, duty_cycle = get_current_window(config.TIME_WINDOWS,
                                                current_time_tuple)
        
        # Get window start/end times for status and notifications
        window_start = None
        window_end = None
        if window and window in config.TIME_WINDOWS:
            window_config = config.TIME_WINDOWS[window]
            window_start = window_config.get("start")
            window_end = window_config.get("end")
            
            # For day window, use actual sunrise/sunset times
            if window == "day":
                month = current_time_tuple[1]
                day = current_time_tuple[2]
                sunrise_h, sunrise_m, sunset_h, sunset_m = sun_times_leh.get_sunrise_sunset(month, day)
                window_start = int_to_time_str(sunrise_h, sunrise_m)
                window_end = int_to_time_str(sunset_h, sunset_m)
        
        if window:
            log.info(f"Active window: {window}, setting duty cycle: {duty_cycle}%")
            led_pwm.set_duty_percent(duty_cycle)
            
            # Update system status
            system_status.update_led_status(duty_cycle, window, window_start, window_end)
            
            # Send MQTT notification if window changed
            mqtt_notifier.notify_window_change(window, duty_cycle, window_start, window_end)
        else:
            log.warn("No active window detected, turning LED off")
            led_pwm.set_duty_percent(0)
            
            # Update system status for no active window
            system_status.update_led_status(0, None, None, None)
            
    except Exception as e:
        error_msg = f"Error updating LED: {e}"
        log.error(error_msg)
        
        # Record error in system status
        system_status.record_error(error_msg)
        
        # Send error notification
        mqtt_notifier.notify_error(error_msg)
        
        # Turn off LED in case of error
        led_pwm.set_duty_percent(0)
        system_status.update_led_status(0, None, None, None)


def main_loop():
    """
    Main loop that repeatedly updates the LED PWM and handles web requests.
    
    The loop now integrates web server request handling with LED updates,
    and supports runtime configuration reloading when updates are received
    via the web interface.
    """
    last_led_update = 0
    web_request_interval = 0.1  # Handle web requests every 100ms
    
    while True:
        try:
            current_time = time.time()
            
            # Handle web requests frequently (non-blocking)
            if web_server.running:
                web_server.handle_requests(timeout=web_request_interval)
            
            # Update LED based on configured interval
            if current_time - last_led_update >= config.UPDATE_INTERVAL:
                # Check if configuration was updated via web interface
                if config.config_manager.config != config.config_manager.get_config_dict():
                    log.info("Configuration change detected, reloading...")
                    config.config_manager.reload()
                    # Re-initialize PWM controller if pin or frequency changed
                    global led_pwm
                    led_pwm.deinit()
                    led_pwm = PWMController(freq=config.PWM_FREQUENCY, pin=config.LED_PWM_PIN)
                
                update_led()
                last_led_update = current_time
            else:
                # Short sleep to prevent excessive CPU usage
                time.sleep(web_request_interval)
                
        except KeyboardInterrupt:
            log.info("Shutdown requested")
            if web_server.running:
                web_server.stop()
            break
        except Exception as e:
            log.error(f"Error in main loop: {e}")
            time.sleep(1)  # Brief pause on error


# Start the main loop automatically when the module is loaded
main_loop()

