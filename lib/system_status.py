"""
System status tracking for PagodaLightPico

Maintains current system state including LED status, active window,
and other runtime information for display on web interface and API endpoints.
"""

import time
import rtc_module
import sun_times_leh
from lib.config_manager import config_manager
from simple_logger import Logger

log = Logger()

class SystemStatus:
    """
    Tracks and provides current system status information.
    
    Maintains state about current LED duty cycle, active time window,
    system uptime, and other runtime information.
    """
    
    def __init__(self):
        self.startup_time = time.time()
        self.current_duty_cycle = 0
        self.current_window = None
        self.current_window_start = None
        self.current_window_end = None
        self.last_update_time = 0
        self.total_updates = 0
        self.error_count = 0
        self.last_error = None
        self.wifi_connected = False
        self.mqtt_connected = False
        self.web_server_running = False
        self.mdns_running = False
    
    def update_led_status(self, duty_cycle, window_name=None, start_time=None, end_time=None):
        """
        Update current LED status.
        
        Args:
            duty_cycle (int): Current PWM duty cycle percentage (0-100)
            window_name (str): Name of active time window
            start_time (str): Window start time (HH:MM)  
            end_time (str): Window end time (HH:MM)
        """
        self.current_duty_cycle = duty_cycle
        self.current_window = window_name
        self.current_window_start = start_time
        self.current_window_end = end_time
        self.last_update_time = time.time()
        self.total_updates += 1
        
        log.debug(f"[STATUS] Updated: {duty_cycle}% duty cycle, window: {window_name}")
    
    def record_error(self, error_message):
        """
        Record system error.
        
        Args:
            error_message (str): Error description
        """
        self.error_count += 1
        self.last_error = {
            "message": error_message,
            "timestamp": time.time()
        }
        log.debug(f"[STATUS] Error recorded: {error_message}")
    
    def set_connection_status(self, wifi=None, mqtt=None, web_server=None, mdns=None):
        """
        Update connection status.
        
        Args:
            wifi (bool): WiFi connection status
            mqtt (bool): MQTT connection status  
            web_server (bool): Web server running status
            mdns (bool): mDNS service running status
        """
        if wifi is not None:
            self.wifi_connected = wifi
        if mqtt is not None:
            self.mqtt_connected = mqtt
        if web_server is not None:
            self.web_server_running = web_server
        if mdns is not None:
            self.mdns_running = mdns
    
    def get_current_time_info(self):
        """
        Get current time and sunrise/sunset information.
        
        Returns:
            dict: Time information including current time, sunrise, sunset
        """
        try:
            current_time_tuple = rtc_module.get_current_time()
            month = current_time_tuple[1]
            day = current_time_tuple[2]
            
            # Get sunrise/sunset times
            sunrise_h, sunrise_m, sunset_h, sunset_m = sun_times_leh.get_sunrise_sunset(month, day)
            
            # Format current time
            current_time_str = f"{current_time_tuple[3]:02d}:{current_time_tuple[4]:02d}:{current_time_tuple[5]:02d}"
            current_date_str = f"{current_time_tuple[2]:02d}/{current_time_tuple[1]:02d}/{current_time_tuple[0]}"
            
            return {
                "current_time": current_time_str,
                "current_date": current_date_str,
                "sunrise_time": f"{sunrise_h:02d}:{sunrise_m:02d}",
                "sunset_time": f"{sunset_h:02d}:{sunset_m:02d}",
                "timezone": config_manager.TIMEZONE_NAME
            }
        except Exception as e:
            log.error(f"[STATUS] Error getting time info: {e}")
            return {
                "current_time": "Unknown",
                "current_date": "Unknown", 
                "sunrise_time": "Unknown",
                "sunset_time": "Unknown",
                "timezone": "Unknown"
            }
    
    def get_uptime(self):
        """
        Get system uptime in seconds.
        
        Returns:
            float: Uptime in seconds
        """
        return time.time() - self.startup_time
    
    def get_uptime_string(self):
        """
        Get formatted uptime string.
        
        Returns:
            str: Human-readable uptime
        """
        uptime_seconds = self.get_uptime()
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_network_info(self):
        """
        Get network status information.
        
        Returns:
            dict: Network status information
        """
        try:
            # Import here to avoid circular imports
            from lib.wifi_connect import get_network_status
            return get_network_status()
        except Exception as e:
            log.error(f"[STATUS] Error getting network info: {e}")
            return {
                "active": False,
                "connected": False,
                "hostname": None,
                "ip": None,
                "gateway": None,
                "dns": None,
                "signal_strength": None
            }
    
    def get_status_dict(self):
        """
        Get complete system status as dictionary.
        
        Returns:
            dict: Complete system status information
        """
        time_info = self.get_current_time_info()
        network_info = self.get_network_info()
        
        return {
            "system": {
                "uptime": self.get_uptime(),
                "uptime_string": self.get_uptime_string(),
                "total_updates": self.total_updates,
                "error_count": self.error_count,
                "last_error": self.last_error
            },
            "connections": {
                "wifi": self.wifi_connected,
                "mqtt": self.mqtt_connected,
                "web_server": self.web_server_running,
                "mdns": self.mdns_running
            },
            "network": network_info,
            "led": {
                "duty_cycle": self.current_duty_cycle,
                "duty_cycle_display": f"{self.current_duty_cycle}%",
                "status": "ON" if self.current_duty_cycle > 0 else "OFF"
            },
            "time_window": {
                "current": self.current_window,
                "current_display": self.current_window.replace('_', ' ').title() if self.current_window else "None",
                "start_time": self.current_window_start,
                "end_time": self.current_window_end,
                "last_update": self.last_update_time
            },
            "time": time_info,
            "config": {
                "update_interval": config_manager.UPDATE_INTERVAL,
                "log_level": config_manager.LOG_LEVEL,
                "notifications_enabled": getattr(config_manager, 'NOTIFICATIONS_ENABLED', False)
            }
        }
    
    def get_status_summary(self):
        """
        Get brief status summary for logging.
        
        Returns:
            str: Status summary string
        """
        time_info = self.get_current_time_info()
        window_display = self.current_window.replace('_', ' ').title() if self.current_window else "None"
        
        return (f"LED: {self.current_duty_cycle}%, "
                f"Window: {window_display}, "
                f"Time: {time_info['current_time']}, "
                f"Uptime: {self.get_uptime_string()}")


# Global system status instance
system_status = SystemStatus()
