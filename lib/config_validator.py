"""
Configuration validation module for PagodaLightPico.

This module provides functions to validate the configuration values
and ensure they are within acceptable ranges.
"""

import config


def validate_config():
    """
    Validate all configuration values.
    
    Returns:
        list: List of validation errors. Empty list if all validations pass.
    """
    errors = []
    
    # Validate TIMEZONE_OFFSET
    if not isinstance(config.TIMEZONE_OFFSET, (int, float)):
        errors.append("TIMEZONE_OFFSET must be a number")
    elif config.TIMEZONE_OFFSET < -12 or config.TIMEZONE_OFFSET > 14:
        errors.append("TIMEZONE_OFFSET must be between -12 and 14")
    
    # Validate RTC I2C pins
    if not isinstance(config.RTC_I2C_SDA_PIN, int):
        errors.append("RTC_I2C_SDA_PIN must be an integer")
    elif config.RTC_I2C_SDA_PIN < 0 or config.RTC_I2C_SDA_PIN > 29:
        errors.append("RTC_I2C_SDA_PIN must be between 0 and 29")
        
    if not isinstance(config.RTC_I2C_SCL_PIN, int):
        errors.append("RTC_I2C_SCL_PIN must be an integer")
    elif config.RTC_I2C_SCL_PIN < 0 or config.RTC_I2C_SCL_PIN > 29:
        errors.append("RTC_I2C_SCL_PIN must be between 0 and 29")
    
    # Validate LED_PWM_PIN
    if not isinstance(config.LED_PWM_PIN, int):
        errors.append("LED_PWM_PIN must be an integer")
    elif config.LED_PWM_PIN < 0 or config.LED_PWM_PIN > 29:
        errors.append("LED_PWM_PIN must be between 0 and 29")
    
    # Validate PWM_FREQUENCY
    if not isinstance(config.PWM_FREQUENCY, int):
        errors.append("PWM_FREQUENCY must be an integer")
    elif config.PWM_FREQUENCY <= 0:
        errors.append("PWM_FREQUENCY must be positive")
    
    # Validate LOG_LEVEL
    valid_log_levels = ['FATAL', 'ERROR', 'WARN', 'INFO', 'DEBUG']
    if config.LOG_LEVEL not in valid_log_levels:
        errors.append(f"LOG_LEVEL must be one of {valid_log_levels}")
    
    # Validate UPDATE_INTERVAL
    if not isinstance(config.UPDATE_INTERVAL, int):
        errors.append("UPDATE_INTERVAL must be an integer")
    elif config.UPDATE_INTERVAL <= 0:
        errors.append("UPDATE_INTERVAL must be positive")
    
    # Validate TIME_WINDOWS
    if not isinstance(config.TIME_WINDOWS, dict):
        errors.append("TIME_WINDOWS must be a dictionary")
    else:
        for window_name, window in config.TIME_WINDOWS.items():
            if not isinstance(window, dict):
                errors.append(f"Window '{window_name}' must be a dictionary")
                continue
                
            # Check required keys
            if "start" not in window:
                errors.append(f"Window '{window_name}' missing 'start' key")
            if "end" not in window:
                errors.append(f"Window '{window_name}' missing 'end' key")
            if "duty_cycle" not in window:
                errors.append(f"Window '{window_name}' missing 'duty_cycle' "
                              f"key")
                
            # Validate time format
            if "start" in window:
                if (not isinstance(window["start"], str) or
                        len(window["start"]) != 5):
                    errors.append(f"Window '{window_name}' start time must be "
                                  f"in HH:MM format")
                else:
                    try:
                        hour, minute = map(int, window["start"].split(":"))
                        if (hour < 0 or hour > 23 or
                                minute < 0 or minute > 59):
                            errors.append(f"Window '{window_name}' start time "
                                          f"must be valid (00:00-23:59)")
                    except ValueError:
                        errors.append(f"Window '{window_name}' start time must "
                                      f"be in HH:MM format")
                        
            if "end" in window:
                if (not isinstance(window["end"], str) or
                        len(window["end"]) != 5):
                    errors.append(f"Window '{window_name}' end time must be "
                                  f"in HH:MM format")
                else:
                    try:
                        hour, minute = map(int, window["end"].split(":"))
                        if (hour < 0 or hour > 23 or
                                minute < 0 or minute > 59):
                            errors.append(f"Window '{window_name}' end time "
                                          f"must be valid (00:00-23:59)")
                    except ValueError:
                        errors.append(f"Window '{window_name}' end time must "
                                      f"be in HH:MM format")
                        
            # Validate duty_cycle
            if "duty_cycle" in window:
                if not isinstance(window["duty_cycle"], int):
                    errors.append(f"Window '{window_name}' duty_cycle must "
                                  f"be an integer")
                elif (window["duty_cycle"] < 0 or
                      window["duty_cycle"] > 100):
                    errors.append(f"Window '{window_name}' duty_cycle must "
                                  f"be between 0 and 100")
    
    return errors