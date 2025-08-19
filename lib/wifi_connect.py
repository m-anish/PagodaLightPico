"""
WiFi connection and NTP time synchronization module.

Handles:
- Connecting to WiFi network using credentials from config.
- Synchronizing system RTC time from NTP server with timezone adjustment.
- Writing updated time to DS3231 RTC using urtc library.
- Controls LED status for connection state.
- Logs status messages using the custom Logger.
"""

import network
import time
import ntptime
from lib.config_manager import WIFI_SSID, WIFI_PASSWORD, TIMEZONE_OFFSET
from machine import Pin
import urtc
from simple_logger import Logger
from lib.rtc_shared import rtc

led = Pin(25, Pin.OUT)
log = Logger()


def connect_wifi(timeout=10):
    """
    Connects to WiFi using credentials from config file.

    Args:
        timeout (int): How many seconds to wait before giving up.

    Returns:
        bool: True if connected, False on failure.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    log.info("[WIFI] Starting connection attempt")

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                log.error("[WIFI] Connection timed out after {} seconds"
                          .format(timeout))
                led.value(0)  # LED OFF when not connected
                return False
            time.sleep(0.1)
        log.info("[WIFI] Connected with IP: {}".format(wlan.ifconfig()[0]))
    else:
        log.info("[WIFI] Already connected")
    led.value(1)  # LED ON when connected
    return True


def sync_time_ntp():
    """
    Synchronize system time from NTP server using ntptime.

    Applies timezone offset from config and writes corrected time back to
    DS3231 RTC.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        log.info("[NTP] Starting time synchronization")
        ntptime.settime()  # syncs to UTC time
        log.debug("[NTP] settime() completed successfully")

        # Get current UTC timestamp in seconds
        utc_sec = time.time()
        log.debug(f"[NTP] System RTC time after sync (UTC seconds): {utc_sec}")

        # Apply timezone offset in seconds
        offset_sec = int(TIMEZONE_OFFSET * 3600)
        log.debug(f"[NTP] Timezone offset in seconds (from config): {offset_sec}")

        local_sec = utc_sec + offset_sec
        log.debug(f"[NTP] Local time in seconds after applying offset: {local_sec}")

        # Convert to tuple compatible with urtc DS3231 datetime
        dt_tuple = urtc.seconds2tuple(local_sec)
        log.debug(f"[NTP] Converted local time tuple for DS3231: {dt_tuple}")

        # Write corrected time to DS3231 RTC
        rtc.datetime(dt_tuple)
        log.info("[NTP] DS3231 RTC datetime updated successfully with local time")

        # Verify by reading back from DS3231 RTC
        readback = rtc.datetime()
        log.debug(f"[NTP] RTC datetime read back for verification: {readback}")

        return True
    except Exception as e:
        log.error(f"[NTP] Time synchronization failed: {e}")
        return False
