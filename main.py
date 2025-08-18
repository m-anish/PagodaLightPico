"""
Main control loop for PWM output based on sunrise and sunset times.

Handles WiFi and NTP sync on boot, daily update of sunrise/sunset times,
and periodic PWM duty adjustment based on current time and schedule.

Logs key events and debug info.
"""

import time
from rtc_module import get_current_time
from sun_times_leh import get_sunrise_sunset
from pwm_control import PWMController
from wifi_connect import connect_wifi, sync_time_ntp
from simple_logger import Logger

log = Logger()

def get_seconds_since_midnight(hours, minutes):
    """
    Convert hours and minutes to seconds since midnight.

    Args:
        hours (int): Hour component.
        minutes (int): Minute component.

    Returns:
        int: Seconds since midnight.
    """
    return hours * 3600 + minutes * 60

log.info("Starting system")

if connect_wifi():
    log.info("WiFi connected successfully")
    if not sync_time_ntp():
        log.warn("Using RTC time due to NTP sync failure")
else:
    log.warn("Using RTC time due to WiFi connection failure")

pwm = PWMController()

last_date = None
sunrise = 0
sunset = 0

while True:
    year, month, day, hour, minute, second, weekday = get_current_time()

    if (year, month, day) != last_date:
        sun_rise_h, sun_rise_m, sun_set_h, sun_set_m = get_sunrise_sunset(month, day)
        sunrise = get_seconds_since_midnight(sun_rise_h, sun_rise_m)
        sunset = get_seconds_since_midnight(sun_set_h, sun_set_m)
        last_date = (year, month, day)
        log.info("Updated sunrise to {:02d}:{:02d} and sunset to {:02d}:{:02d} for {:04d}-{:02d}-{:02d}".format(
            sun_rise_h, sun_rise_m, sun_set_h, sun_set_m, year, month, day))

    now = get_seconds_since_midnight(hour, minute)
    t_2200 = get_seconds_since_midnight(22, 0)
    t_midnight = 0
    t_2hr_before_sunrise = sunrise - 7200 if sunrise - 7200 > 0 else 0

    duty = 0
    if sunrise <= now < sunset:
        duty = 0
    elif sunset <= now < t_2200:
        duty = 90
    elif t_2200 <= now or now == 0:
        duty = 70
    elif t_midnight <= now < t_2hr_before_sunrise:
        duty = 40
    elif t_2hr_before_sunrise <= now < sunrise:
        duty = 90

    pwm.set_duty_percent(duty)
    log.debug("Time {:02d}:{:02d}:{:02d} - PWM duty set to {}%".format(hour, minute, second, duty))
    time.sleep(30)
