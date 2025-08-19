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
from lib.config_manager import WIFI_SSID, WIFI_PASSWORD, TIMEZONE_OFFSET, config_manager
from machine import Pin
import urtc
from simple_logger import Logger
from lib.rtc_shared import rtc

led = Pin(25, Pin.OUT)
log = Logger()


def connect_wifi(timeout=10, max_attempts=3):
    """
    Connects to WiFi using credentials from config file with retry logic.

    Args:
        timeout (int): How many seconds to wait per attempt before giving up.
        max_attempts (int): Maximum number of connection attempts.

    Returns:
        bool: True if connected, False on failure after all attempts.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Set hostname from config
    hostname = config_manager.get_config_dict().get('hostname', 'PagodaLightPico')
    try:
        network.hostname(hostname)
        log.info(f"[WIFI] Set network hostname to: {hostname}")
    except Exception as e:
        log.warn(f"[WIFI] Failed to set hostname: {e}")
    
    # Check if already connected
    if wlan.isconnected():
        ip_info = wlan.ifconfig()
        log.info("[WIFI] Already connected")
        log.info(f"[WIFI] Network Details:")
        log.info(f"[WIFI]   IP Address: {ip_info[0]}")
        log.info(f"[WIFI]   Subnet Mask: {ip_info[1]}")
        log.info(f"[WIFI]   Gateway: {ip_info[2]}")
        log.info(f"[WIFI]   DNS Server: {ip_info[3]}")
        log.info(f"[WIFI] Web interface available at: http://{ip_info[0]}/")
        led.value(1)  # LED ON when connected
        return True
    
    # Attempt to connect with retries
    for attempt in range(1, max_attempts + 1):
        log.info(f"[WIFI] Connection attempt {attempt}/{max_attempts}")
        
        try:
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            start = time.time()
            
            # Wait for connection or timeout
            while not wlan.isconnected():
                if time.time() - start > timeout:
                    log.warn(f"[WIFI] Attempt {attempt} timed out after {timeout} seconds")
                    break
                time.sleep(0.1)
            
            # Check if connection was successful
            if wlan.isconnected():
                ip_info = wlan.ifconfig()
                log.info(f"[WIFI] Connected successfully on attempt {attempt}")
                log.info(f"[WIFI] Network Details:")
                log.info(f"[WIFI]   IP Address: {ip_info[0]}")
                log.info(f"[WIFI]   Subnet Mask: {ip_info[1]}")
                log.info(f"[WIFI]   Gateway: {ip_info[2]}")
                log.info(f"[WIFI]   DNS Server: {ip_info[3]}")
                log.info(f"[WIFI] Web interface will be available at: http://{ip_info[0]}/")
                led.value(1)  # LED ON when connected
                return True
            
        except Exception as e:
            log.error(f"[WIFI] Connection attempt {attempt} failed with error: {e}")
        
        # Wait before retry (except on last attempt)
        if attempt < max_attempts:
            log.info(f"[WIFI] Waiting 2 seconds before retry...")
            time.sleep(2)
    
    # All attempts failed
    log.error(f"[WIFI] Failed to connect after {max_attempts} attempts")
    led.value(0)  # LED OFF when not connected
    return False


def get_network_status():
    """
    Get current network connection status and information.
    
    Returns:
        dict: Network status information including connection state, IP, etc.
    """
    wlan = network.WLAN(network.STA_IF)
    
    if not wlan.active():
        return {
            "active": False,
            "connected": False,
            "hostname": None,
            "ip": None,
            "gateway": None,
            "dns": None,
            "signal_strength": None
        }
    
    connected = wlan.isconnected()
    ip_info = wlan.ifconfig() if connected else [None, None, None, None]
    
    # Get hostname if available
    hostname = None
    try:
        hostname = network.hostname()
    except:
        pass
    
    # Get signal strength if connected
    signal_strength = None
    if connected:
        try:
            signal_strength = wlan.status('rssi')
        except:
            pass
    
    return {
        "active": wlan.active(),
        "connected": connected,
        "hostname": hostname,
        "ip": ip_info[0],
        "subnet": ip_info[1],
        "gateway": ip_info[2],
        "dns": ip_info[3],
        "signal_strength": signal_strength
    }


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
