"""
MQTT Notification system for PagodaLightPico

Sends push notifications about time window changes and system events
via MQTT broker for delivery to mobile devices.

Supported notification methods:
- MQTT → Pushover (recommended)
- MQTT → Home Assistant → Mobile app
- MQTT → Telegram Bot
- MQTT → Custom webhook services
"""

import json
import time
from lib.config_manager import config_manager
from simple_logger import Logger

# Try to import MQTT library (may not be available in all MicroPython builds)
try:
    from umqtt.simple import MQTTClient
    MQTT_AVAILABLE = True
except ImportError:
    try:
        from mqtt.simple import MQTTClient
        MQTT_AVAILABLE = True
    except ImportError:
        MQTT_AVAILABLE = False

log = Logger()

class MQTTNotifier:
    """
    MQTT-based notification system for sending push notifications.
    
    Connects to configured MQTT broker and publishes notification messages
    that can be consumed by various push notification services.
    """
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.last_window = None
        self.notifications_enabled = False
        self._load_config()
    
    def _load_config(self):
        """Load MQTT configuration from config manager."""
        config = config_manager.get_config_dict()
        notifications = config.get('notifications', {})
        
        self.notifications_enabled = notifications.get('enabled', False)
        self.broker = notifications.get('mqtt_broker', 'broker.hivemq.com')
        self.port = notifications.get('mqtt_port', 1883)
        self.topic = notifications.get('mqtt_topic', 'pagoda_light/notifications')
        self.client_id = notifications.get('mqtt_client_id', 'pagoda_light_pico')
        self.notify_window_change = notifications.get('notify_on_window_change', True)
        self.notify_errors = notifications.get('notify_on_errors', True)
    
    def connect(self):
        """Connect to MQTT broker."""
        if not MQTT_AVAILABLE:
            log.warn("MQTT library not available - notifications disabled")
            return False
        
        if not self.notifications_enabled:
            log.debug("Notifications disabled in configuration")
            return False
        
        try:
            self.client = MQTTClient(self.client_id, self.broker, port=self.port)
            self.client.connect()
            self.connected = True
            log.info(f"Connected to MQTT broker {self.broker}:{self.port}")
            
            # Send startup notification
            self._send_notification("system", {
                "event": "system_startup",
                "message": "🏯 PagodaLight system started",
                "timestamp": time.time(),
                "device": self.client_id
            })
            
            return True
            
        except Exception as e:
            log.error(f"Failed to connect to MQTT broker: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client and self.connected:
            try:
                # Send shutdown notification
                self._send_notification("system", {
                    "event": "system_shutdown", 
                    "message": "🏯 PagodaLight system stopping",
                    "timestamp": time.time(),
                    "device": self.client_id
                })
                self.client.disconnect()
                log.info("Disconnected from MQTT broker")
            except Exception as e:
                log.error(f"Error disconnecting from MQTT: {e}")
            finally:
                self.connected = False
    
    def notify_window_change(self, window_name, duty_cycle, start_time, end_time):
        """
        Send notification when time window changes.
        
        Args:
            window_name (str): Name of the active window
            duty_cycle (int): LED brightness percentage (0-100)
            start_time (str): Window start time (HH:MM)
            end_time (str): Window end time (HH:MM)
        """
        if not self.notify_window_change or not self.connected:
            return
        
        # Only notify if window actually changed
        if self.last_window == window_name:
            return
            
        self.last_window = window_name
        
        # Format notification message
        if window_name == "day":
            icon = "🌅"
            description = "Day (sunrise to sunset)"
        elif duty_cycle == 0:
            icon = "🌙"  
            description = f"Lights off"
        else:
            icon = "💡"
            description = f"Meditation lighting"
        
        message = f"{icon} {description} - {duty_cycle}% brightness"
        
        notification_data = {
            "event": "window_change",
            "window": window_name,
            "duty_cycle": duty_cycle,
            "start_time": start_time,
            "end_time": end_time,
            "message": message,
            "timestamp": time.time(),
            "device": self.client_id
        }
        
        self._send_notification("window_change", notification_data)
        log.info(f"Sent window change notification: {message}")
    
    def notify_error(self, error_message):
        """
        Send notification for system errors.
        
        Args:
            error_message (str): Error description
        """
        if not self.notify_errors or not self.connected:
            return
        
        notification_data = {
            "event": "error",
            "message": f"⚠️ PagodaLight Error: {error_message}",
            "timestamp": time.time(),
            "device": self.client_id,
            "severity": "error"
        }
        
        self._send_notification("error", notification_data)
        log.info(f"Sent error notification: {error_message}")
    
    def notify_config_change(self):
        """Send notification when configuration is updated."""
        if not self.connected:
            return
        
        notification_data = {
            "event": "config_update",
            "message": "⚙️ Configuration updated via web interface",
            "timestamp": time.time(),
            "device": self.client_id
        }
        
        self._send_notification("config", notification_data)
        log.info("Sent configuration change notification")
    
    def _send_notification(self, category, data):
        """
        Send notification via MQTT.
        
        Args:
            category (str): Notification category (window_change, error, system, config)
            data (dict): Notification data
        """
        if not self.client or not self.connected:
            return
        
        try:
            # Create topic with category
            topic = f"{self.topic}/{category}"
            
            # Convert data to JSON
            message = json.dumps(data)
            
            # Publish message
            self.client.publish(topic, message)
            log.debug(f"Published notification to {topic}")
            
        except Exception as e:
            log.error(f"Failed to send MQTT notification: {e}")
            # Try to reconnect on next notification
            self.connected = False
    
    def reload_config(self):
        """Reload configuration and reconnect if needed."""
        old_enabled = self.notifications_enabled
        old_broker = self.broker
        old_port = self.port
        
        self._load_config()
        
        # Reconnect if configuration changed
        if (self.notifications_enabled != old_enabled or 
            self.broker != old_broker or 
            self.port != old_port):
            
            if self.connected:
                self.disconnect()
            
            if self.notifications_enabled:
                self.connect()
    
    def get_status(self):
        """Get current MQTT connection status."""
        return {
            "mqtt_available": MQTT_AVAILABLE,
            "notifications_enabled": self.notifications_enabled,
            "connected": self.connected,
            "broker": self.broker if self.notifications_enabled else None,
            "topic": self.topic if self.notifications_enabled else None
        }


# Global MQTT notifier instance
mqtt_notifier = MQTTNotifier()
