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
            if not os.path.exists(self.config_file):
                log.error(f"Configuration file {self.config_file} not found")
                raise FileNotFoundError(f"Configuration file {self.config_file} not found")
            
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            
            log.info(f"Configuration loaded from {self.config_file}")
            self._validate_config()
            
        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            raise
    
    def save_config(self):
        """Save current configuration to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            log.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            log.error(f"Failed to save configuration: {e}")
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
            # Deep merge the updates into current config
            self._deep_merge(self.config, updates)
            
            # Validate the updated configuration
            self._validate_config()
            
            # Update attributes for backward compatibility
            self._setup_attributes()
            
            # Save to file
            return self.save_config()
            
        except Exception as e:
            log.error(f"Failed to update configuration: {e}")
            return False
    
    def _deep_merge(self, base_dict, update_dict):
        """Deep merge update_dict into base_dict."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _setup_attributes(self):
        """Set up attributes for backward compatibility with config.py format."""
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
        self.LED_PWM_PIN = hardware.get("led_pwm_pin", 16)
        self.PWM_FREQUENCY = hardware.get("pwm_frequency", 1000)
        
        # System settings
        system = self.config.get("system", {})
        self.LOG_LEVEL = system.get("log_level", "INFO")
        self.UPDATE_INTERVAL = system.get("update_interval", 60)
        
        # Time windows
        self.TIME_WINDOWS = self.config.get("time_windows", {})
    
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
        pins_to_check = ["rtc_i2c_sda_pin", "rtc_i2c_scl_pin", "led_pwm_pin"]
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
        
        # Validate time windows
        time_windows = self.config.get("time_windows", {})
        for window_name, window_config in time_windows.items():
            if not isinstance(window_config, dict):
                continue
            
            # Skip comment fields
            if window_name.startswith("_"):
                continue
            
            # Validate time format
            for time_field in ["start", "end"]:
                time_value = window_config.get(time_field)
                if not self._is_valid_time_format(time_value):
                    errors.append(f"Invalid time format for {window_name}.{time_field}: {time_value}")
            
            # Validate duty cycle
            duty_cycle = window_config.get("duty_cycle")
            if not isinstance(duty_cycle, int) or duty_cycle < 0 or duty_cycle > 100:
                errors.append(f"Duty cycle for {window_name} must be between 0 and 100")
        
        if errors:
            error_msg = "Configuration validation failed: " + "; ".join(errors)
            log.error(error_msg)
            raise ValueError(error_msg)
        
        log.debug("Configuration validation passed")
    
    def _is_valid_time_format(self, time_str):
        """Validate time format HH:MM."""
        if not isinstance(time_str, str):
            return False
        
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
        log.info("Reloading configuration from file")
        self.load_config()
        self._setup_attributes()


# Global configuration instance for backward compatibility
config_manager = ConfigManager()

# Export attributes at module level for backward compatibility
WIFI_SSID = config_manager.WIFI_SSID
WIFI_PASSWORD = config_manager.WIFI_PASSWORD
TIMEZONE_NAME = config_manager.TIMEZONE_NAME
TIMEZONE_OFFSET = config_manager.TIMEZONE_OFFSET
RTC_I2C_SDA_PIN = config_manager.RTC_I2C_SDA_PIN
RTC_I2C_SCL_PIN = config_manager.RTC_I2C_SCL_PIN
LED_PWM_PIN = config_manager.LED_PWM_PIN
PWM_FREQUENCY = config_manager.PWM_FREQUENCY
LOG_LEVEL = config_manager.LOG_LEVEL
UPDATE_INTERVAL = config_manager.UPDATE_INTERVAL
TIME_WINDOWS = config_manager.TIME_WINDOWS
