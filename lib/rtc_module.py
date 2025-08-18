"""
RTC module using the uRTC library's DS3231 driver.

Provides current date and time from the DS3231 real-time clock over I2C.

Note:
- Timezone offset is NOT applied here to avoid double offsetting,
  since the DS3231 RTC stores local time adjusted during write.
- Returns the raw datetime from the DS3231.

The time tuple format used is DateTimeTuple(year, month, day, weekday, hour, minute, second, millisecond).

Requires: micropython-urtc library with DS3231 support.
"""

from machine import I2C, Pin
import urtc
from config import RTC_I2C_SDA_PIN, RTC_I2C_SCL_PIN
from simple_logger import Logger

log = Logger()

# Initialize I2C bus for RTC
i2c = I2C(0, scl=Pin(RTC_I2C_SCL_PIN), sda=Pin(RTC_I2C_SDA_PIN))

# Create DS3231 instance from urtc library
rtc = urtc.DS3231(i2c)

def get_current_time():
    """
    Get current date and time directly from the DS3231 RTC without offset.

    Returns:
        tuple: (year, month, day, hour, minute, second, weekday)
            where weekday is 1=Monday ... 7=Sunday
    """
    dt = rtc.datetime()  # DateTimeTuple(year, month, day, weekday, hour, minute, second, millisecond)

    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    second = dt.second
    weekday = dt.weekday

    log.debug("RTC current time read (no offset): {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} Weekday: {}".format(
        year, month, day, hour, minute, second, weekday))

    return (year, month, day, hour, minute, second, weekday)
