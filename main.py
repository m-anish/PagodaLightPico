"""
main.py

Main application script for PagodaLightPico.

Controls LED lighting PWM duty cycle based on configurable time windows
and dynamically calculated sunrise and sunset times from sun_times_leh module.

The "day" time window start and end times are set dynamically each check
based on the current date's sunrise and sunset times.

Other time windows are configured statically in config.py.

The script reads real-time clock (RTC) time using rtc_module and sets PWM
on an assigned GPIO pin accordingly.

Logging is done via simple_logger with timestamps and levels.
"""

from lib import config_manager as config
import sun_times_leh
import rtc_module
from simple_logger import Logger
from wifi_connect import connect_wifi, sync_time_ntp
import time
from lib.pwm_control import PWMController

log = Logger()

# Initialize PWM controller
led_pwm = PWMController(freq=config.PWM_FREQUENCY, pin=config.LED_PWM_PIN)

log.info("Starting system")

if connect_wifi():
    log.info("WiFi connected successfully")
    if not sync_time_ntp():
        log.warn("Using RTC time due to NTP sync failure")
else:
    log.warn("Using RTC time due to WiFi connection failure")


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
    based on the active time window.
    """
    try:
        current_time = rtc_module.get_current_time()
        window, duty_cycle = get_current_window(config.TIME_WINDOWS,
                                                current_time)
        if window:
            log.info(f"Active window: {window}, setting duty cycle: "
                     f"{duty_cycle}%")
            led_pwm.set_duty_percent(duty_cycle)
        else:
            log.warn("No active window detected, turning LED off")
            led_pwm.set_duty_percent(0)
    except Exception as e:
        log.error(f"Error updating LED: {e}")
        # Turn off LED in case of error
        led_pwm.set_duty_percent(0)


def main_loop():
    """
    Main loop that repeatedly updates the LED PWM every configured interval.
    """
    while True:
        try:
            update_led()
        except Exception as e:
            log.error(f"Error in main loop: {e}")
        finally:
            time.sleep(config.UPDATE_INTERVAL)


if __name__ == "__main__":
    main_loop()

