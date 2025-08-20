"""
Configuration manager for PagodaLightPico

Handles loading, saving, and validating JSON configuration.
Provides backward compatibility with the old config.py format.
Supports runtime configuration updates.
"""

import json
import os

# Initialize a basic logger to avoid circular imports during config loading
class BasicLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")
    def warn(self, msg): print(f"WARN: {msg}")

log = BasicLogger()

class ConfigManager:
    """
    Manages JSON configuration with validation and runtime updates.
    
    Provides attribute access to configuration values for backward compatibility
    with modules that used config.py imports.
    """
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = {}
        self.load_config()
        self._setup_attributes()
    
    def load_config(self):
        """Load configuration from JSON file."""
        try:
            # Check if file exists
            os.stat(self.config_file)
            
            # Load and parse JSON with minimal memory usage
            with open(self.config_file, 'r') as f:
                # For MicroPython, we don't have many options to optimize JSON parsing
                # but we can ensure we're not keeping unnecessary references
                self.config = json.load(f)
            
            # Reduce logging to save memory
            # log.info(f"[CONFIG] Configuration loaded from {self.config_file}")
            self._validate_config()
            
        except Exception as e:
            # Reduce logging to save memory
            # log.error(f"[CONFIG] Failed to load configuration: {e}")
            raise
    
    def save_config(self):
        """Save current configuration to JSON file."""
        try:
            # For MicroPython, we don't have many options to optimize JSON writing
            # but we can ensure we're not keeping unnecessary references
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f)
            # Reduce logging to save memory
            # log.info(f"[CONFIG] Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            # Reduce logging to save memory
            # log.error(f"[CONFIG] Failed to save configuration: {e}")
            return False
    
    def update_config(self, updates):
        """
        Update configuration with new values.
        
        Args:
            updates (dict): Dictionary of configuration updates in nested format
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Debug: Log the updates being applied
            log.debug(f"[CONFIG] Applying updates: {updates}")
            
            # Deep merge the updates into current config
            self._deep_merge(self.config, updates)
            
            # Debug: Log the updated config
            log.debug(f"[CONFIG] Updated config PWM pins: {self.config.get('pwm_pins', {})}")
            
            # Validate the updated configuration
            self._validate_config()
            
            # Update attributes for backward compatibility
            self._setup_attributes()
            
            # Save to file
            return self.save_config()
            
        except Exception as e:
            log.error(f"[CONFIG] Failed to update configuration: {e}")
            return False
    
    def _deep_merge(self, base_dict, update_dict):
        """Deep merge update_dict into base_dict."""
        log.debug(f"[CONFIG] Deep merging: base={base_dict}, update={update_dict}")
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                log.debug(f"[CONFIG] Recursively merging key {key}")
                self._deep_merge(base_dict[key], value)
            else:
                log.debug(f"[CONFIG] Setting key {key} to {value}")
                base_dict[key] = value
    
    def _setup_attributes(self):
        """Set up attributes for module-level access."""
        # WiFi settings
        self.WIFI_SSID = self.config.get("wifi", {}).get("ssid", "")
        self.WIFI_PASSWORD = self.config.get("wifi", {}).get("password", "")
        
        # Timezone settings
        self.TIMEZONE_NAME = self.config.get("timezone", {}).get("name", "UTC")
        self.TIMEZONE_OFFSET = self.config.get("timezone", {}).get("offset", 0.0)
        
        # Hardware settings
        hardware = self.config.get("hardware", {})
        self.RTC_I2C_SDA_PIN = hardware.get("rtc_i2c_sda_pin", 20)
        self.RTC_I2C_SCL_PIN = hardware.get("rtc_i2c_scl_pin", 21)
        self.PWM_FREQUENCY = hardware.get("pwm_frequency", 1000)
        
        # System settings
        system = self.config.get("system", {})
        self.LOG_LEVEL = system.get("log_level", "INFO")
        self.UPDATE_INTERVAL = system.get("update_interval", 120)
        # New: backoff/sleep tunables (milliseconds)
        self.SERVER_IDLE_SLEEP_MS = system.get("server_idle_sleep_ms", 300)
        self.CLIENT_READ_SLEEP_MS = system.get("client_read_sleep_ms", 50)
        # New: network monitor interval (seconds)
        self.NETWORK_CHECK_INTERVAL = system.get("network_check_interval", 120)
        # New: RAM telemetry settings
        self.RAM_TELEMETRY_ENABLED = system.get("ram_telemetry_enabled", False)
        self.RAM_TELEMETRY_INTERVAL = system.get("ram_telemetry_interval", 300)
        # New: Web UI title
        self.WEB_TITLE = system.get("web_title", "PagodaLightPico")
        
        # Notification settings  
        notifications = self.config.get("notifications", {})
        self.NOTIFICATIONS_ENABLED = notifications.get("enabled", False)
        self.MQTT_BROKER = notifications.get("mqtt_broker", "broker.hivemq.com")
        self.MQTT_PORT = notifications.get("mqtt_port", 1883)
        self.MQTT_TOPIC = notifications.get('mqtt_topic', 'PagodaLightPico/notifications')
        self.MQTT_CLIENT_ID = notifications.get('mqtt_client_id', 'PagodaLightPico')
        self.NOTIFY_ON_WINDOW_CHANGE = notifications.get("notify_on_window_change", True)
        self.NOTIFY_ON_ERRORS = notifications.get("notify_on_errors", True)
        
        # PWM pins configuration
        self.PWM_PINS = self.config.get("pwm_pins", {})
    
    def _validate_config(self):
        """Validate configuration values."""
        errors = []
        
        # Validate WiFi settings
        wifi = self.config.get("wifi", {})
        if not wifi.get("ssid"):
            errors.append("WiFi SSID is required")
        if not wifi.get("password"):
            errors.append("WiFi password is required")
        
        # Validate timezone
        timezone = self.config.get("timezone", {})
        offset = timezone.get("offset", 0)
        if not isinstance(offset, (int, float)) or offset < -12 or offset > 14:
            errors.append("Timezone offset must be between -12 and +14 hours")
        
        # Validate hardware pins
        hardware = self.config.get("hardware", {})
        pins_to_check = ["rtc_i2c_sda_pin", "rtc_i2c_scl_pin"]
        for pin_name in pins_to_check:
            pin_value = hardware.get(pin_name)
            if not isinstance(pin_value, int) or pin_value < 0 or pin_value > 28:
                errors.append(f"{pin_name} must be an integer between 0 and 28")
        
        # Validate PWM frequency
        pwm_freq = hardware.get("pwm_frequency", 1000)
        if not isinstance(pwm_freq, int) or pwm_freq < 1 or pwm_freq > 40000000:
            errors.append("PWM frequency must be between 1 Hz and 40 MHz")
        
        # Validate system settings
        system = self.config.get("system", {})
        valid_log_levels = ["FATAL", "ERROR", "WARN", "INFO", "DEBUG"]
        if system.get("log_level") not in valid_log_levels:
            errors.append(f"Log level must be one of: {', '.join(valid_log_levels)}")
        
        update_interval = system.get("update_interval", 60)
        if not isinstance(update_interval, int) or update_interval < 1:
            errors.append("Update interval must be a positive integer")
        # Validate network check interval (s)
        network_check_interval = system.get("network_check_interval", 120)
        if not isinstance(network_check_interval, int) or network_check_interval < 10 or network_check_interval > 3600:
            errors.append("system.network_check_interval must be int 10..3600 seconds")
        # Validate server/client sleeps (ms)
        server_idle_ms = system.get("server_idle_sleep_ms", 300)
        client_read_ms = system.get("client_read_sleep_ms", 50)
        if not isinstance(server_idle_ms, int) or server_idle_ms < 50 or server_idle_ms > 5000:
            errors.append("system.server_idle_sleep_ms must be int 50..5000 ms")
        if not isinstance(client_read_ms, int) or client_read_ms < 10 or client_read_ms > 2000:
            errors.append("system.client_read_sleep_ms must be int 10..2000 ms")
        # Validate RAM telemetry
        ram_enabled = system.get("ram_telemetry_enabled", False)
        if not isinstance(ram_enabled, bool):
            errors.append("system.ram_telemetry_enabled must be boolean")
        ram_interval = system.get("ram_telemetry_interval", 300)
        if not isinstance(ram_interval, int) or ram_interval < 10 or ram_interval > 86400:
            errors.append("system.ram_telemetry_interval must be int 10..86400 seconds")
        # Validate web title if provided
        if "web_title" in system and not isinstance(system.get("web_title"), str):
            errors.append("system.web_title must be a string")
        
        # Validate PWM pins configuration
        pwm_pins = self.config.get("pwm_pins", {})
        enabled_pins = 0
        used_gpio_pins = set()
        
        for pin_key, pin_config in pwm_pins.items():
            # Skip comment fields
            if pin_key.startswith("_"):
                continue
                
            if not isinstance(pin_config, dict):
                errors.append(f"PWM pin config {pin_key} must be a dictionary")
                continue
            
            # Validate required fields
            if "gpio_pin" not in pin_config:
                errors.append(f"PWM pin {pin_key} missing gpio_pin")
                continue
                
            gpio_pin = pin_config.get("gpio_pin")
            if not isinstance(gpio_pin, int) or gpio_pin < 0 or gpio_pin > 28:
                errors.append(f"PWM pin {pin_key} gpio_pin must be integer 0-28")
                continue
                
            # Check for duplicate GPIO pins
            if gpio_pin in used_gpio_pins:
                errors.append(f"GPIO pin {gpio_pin} used multiple times")
            used_gpio_pins.add(gpio_pin)
            
            # Check if pin conflicts with I2C pins
            if gpio_pin == hardware.get("rtc_i2c_sda_pin") or gpio_pin == hardware.get("rtc_i2c_scl_pin"):
                errors.append(f"GPIO pin {gpio_pin} conflicts with I2C pins")
            
            # Validate name
            if "name" not in pin_config or not pin_config.get("name"):
                errors.append(f"PWM pin {pin_key} missing name")
            
            # Count enabled pins
            if pin_config.get("enabled", False):
                enabled_pins += 1
                
                # Validate time windows for enabled pins
                time_windows = pin_config.get("time_windows", {})
                if not isinstance(time_windows, dict):
                    errors.append(f"PWM pin {pin_key} time_windows must be a dictionary")
                    continue
                
                # Must have at least day window
                if "day" not in time_windows:
                    errors.append(f"PWM pin {pin_key} must have 'day' time window")
                
                window_count = 0
                for window_name, window_config in time_windows.items():
                    if window_name.startswith("_"):
                        continue
                    window_count += 1
                    
                    if not isinstance(window_config, dict):
                        continue
                    
                    # Validate time format
                    for time_field in ["start", "end"]:
                        time_value = window_config.get(time_field)
                        if not self._is_valid_time_format(time_value):
                            errors.append(f"Invalid time format for {pin_key}.{window_name}.{time_field}: {time_value}")
                    
                    # Validate duty cycle
                    duty_cycle = window_config.get("duty_cycle")
                    if not isinstance(duty_cycle, int) or duty_cycle < 0 or duty_cycle > 100:
                        errors.append(f"Duty cycle for {pin_key}.{window_name} must be between 0 and 100")
                
                # Validate window count (2-5 windows)
                if window_count < 2 or window_count > 5:
                    errors.append(f"PWM pin {pin_key} must have 2-5 time windows")
        
        # Validate pin count (1-5 enabled pins)
        if enabled_pins < 1:
            errors.append("At least one PWM pin must be enabled")
        elif enabled_pins > 5:
            errors.append("Maximum 5 PWM pins can be enabled")
        
        if errors:
            error_msg = "Configuration validation failed: " + "; ".join(errors)
            # Reduce logging to save memory
            # log.error(f"[CONFIG] {error_msg}")
            raise ValueError(error_msg)
        
        # Reduce logging to save memory
        # log.debug("[CONFIG] Validation passed")
    
    def _is_valid_time_format(self, time_str):
        """Validate time format HH:MM."""
        if not isinstance(time_str, str):
            return False

        # Allow dynamic placeholders
        lower = time_str.strip().lower()
        if lower in ("sunrise", "sunset"):
            return True

        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False
            
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, IndexError):
            return False
    
    def get_config_dict(self):
        """Get the complete configuration as a dictionary."""
        return self.config.copy()
    
    def reload(self):
        """Reload configuration from file."""
        log.info("[CONFIG] Reloading configuration from file")
        self.load_config()
        self._setup_attributes()


# Global configuration instance for backward compatibility
config_manager = ConfigManager()

# Export attributes at module level for compatibility
WIFI_SSID = config_manager.WIFI_SSID
WIFI_PASSWORD = config_manager.WIFI_PASSWORD
TIMEZONE_NAME = config_manager.TIMEZONE_NAME
TIMEZONE_OFFSET = config_manager.TIMEZONE_OFFSET
RTC_I2C_SDA_PIN = config_manager.RTC_I2C_SDA_PIN
RTC_I2C_SCL_PIN = config_manager.RTC_I2C_SCL_PIN
PWM_FREQUENCY = config_manager.PWM_FREQUENCY
LOG_LEVEL = config_manager.LOG_LEVEL
UPDATE_INTERVAL = config_manager.UPDATE_INTERVAL
SERVER_IDLE_SLEEP_MS = config_manager.SERVER_IDLE_SLEEP_MS
CLIENT_READ_SLEEP_MS = config_manager.CLIENT_READ_SLEEP_MS
NETWORK_CHECK_INTERVAL = config_manager.NETWORK_CHECK_INTERVAL
RAM_TELEMETRY_ENABLED = config_manager.RAM_TELEMETRY_ENABLED
RAM_TELEMETRY_INTERVAL = config_manager.RAM_TELEMETRY_INTERVAL
PWM_PINS = config_manager.PWM_PINS
WEB_TITLE = config_manager.WEB_TITLE
