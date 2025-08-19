"""
GPIO utility functions for PagodaLightPico.

Provides functions to get available GPIO pins, their capabilities,
and pin validation for the Raspberry Pi Pico W.
"""

from lib.config_manager import config_manager

class GPIOUtils:
    """
    Utility class for GPIO pin management and validation.
    """
    
    # Raspberry Pi Pico W GPIO pin capabilities
    # Based on the official Pico W pinout and datasheet
    GPIO_CAPABILITIES = {
        0: ["GPIO0", "PWM0A", "SPI0_RX", "UART0_TX", "I2C0_SDA"],
        1: ["GPIO1", "PWM0B", "SPI0_CSn", "UART0_RX", "I2C0_SCL"],
        2: ["GPIO2", "PWM1A", "SPI0_SCK", "UART0_CTS", "I2C1_SDA"],
        3: ["GPIO3", "PWM1B", "SPI0_TX", "UART0_RTS", "I2C1_SCL"],
        4: ["GPIO4", "PWM2A", "SPI0_RX", "UART1_TX", "I2C0_SDA"],
        5: ["GPIO5", "PWM2B", "SPI0_CSn", "UART1_RX", "I2C0_SCL"],
        6: ["GPIO6", "PWM3A", "SPI0_SCK", "UART1_CTS", "I2C1_SDA"],
        7: ["GPIO7", "PWM3B", "SPI0_TX", "UART1_RTS", "I2C1_SCL"],
        8: ["GPIO8", "PWM4A", "SPI1_RX", "UART1_TX", "I2C0_SDA"],
        9: ["GPIO9", "PWM4B", "SPI1_CSn", "UART1_RX", "I2C0_SCL"],
        10: ["GPIO10", "PWM5A", "SPI1_SCK", "UART1_CTS", "I2C1_SDA"],
        11: ["GPIO11", "PWM5B", "SPI1_TX", "UART1_RTS", "I2C1_SCL"],
        12: ["GPIO12", "PWM6A", "SPI1_RX", "UART0_TX", "I2C0_SDA"],
        13: ["GPIO13", "PWM6B", "SPI1_CSn", "UART0_RX", "I2C0_SCL"],
        14: ["GPIO14", "PWM7A", "SPI1_SCK", "UART0_CTS", "I2C1_SDA"],
        15: ["GPIO15", "PWM7B", "SPI1_TX", "UART0_RTS", "I2C1_SCL"],
        16: ["GPIO16", "PWM0A", "SPI0_RX", "UART0_TX", "I2C0_SDA"],
        17: ["GPIO17", "PWM0B", "SPI0_CSn", "UART0_RX", "I2C0_SCL"],
        18: ["GPIO18", "PWM1A", "SPI0_SCK", "UART0_CTS", "I2C1_SDA"],
        19: ["GPIO19", "PWM1B", "SPI0_TX", "UART0_RTS", "I2C1_SCL"],
        20: ["GPIO20", "PWM2A", "SPI0_RX", "UART1_TX", "I2C0_SDA"],
        21: ["GPIO21", "PWM2B", "SPI0_CSn", "UART1_RX", "I2C0_SCL"],
        22: ["GPIO22", "PWM3A", "SPI0_SCK", "UART1_CTS", "I2C1_SDA"],
        26: ["GPIO26", "PWM5A", "SPI1_SCK", "UART1_CTS", "I2C1_SDA", "ADC0"],
        27: ["GPIO27", "PWM5B", "SPI1_TX", "UART1_RTS", "I2C1_SCL", "ADC1"],
        28: ["GPIO28", "PWM6A", "SPI1_RX", "UART0_TX", "I2C0_SDA", "ADC2"],
        # GPIO 23, 24, 25 are special purpose
        23: ["GPIO23", "SMPS_MODE"],  # Power supply mode control
        24: ["GPIO24", "VBUS_SENSE"],  # USB power detection
        25: ["GPIO25", "LED_BUILTIN", "PWM4B"],  # Built-in LED
    }
    
    # Pins that should be avoided for general use
    RESTRICTED_PINS = {
        23: "SMPS mode control - avoid for general use",
        24: "VBUS sense - avoid for general use"
    }
    
    @classmethod
    def get_available_pins(cls, exclude_current_usage=True):
        """
        Get list of available GPIO pins for PWM use.
        
        Args:
            exclude_current_usage (bool): If True, exclude pins already configured
            
        Returns:
            dict: {pin_number: [capabilities]} for available pins
        """
        config = config_manager.get_config_dict()
        hardware = config.get('hardware', {})
        
        # Get currently used pins
        used_pins = set()
        if exclude_current_usage:
            # RTC I2C pins from config
            used_pins.add(hardware.get('rtc_i2c_sda_pin'))
            used_pins.add(hardware.get('rtc_i2c_scl_pin'))
            
            # Currently configured PWM pins
            pwm_pins = config.get('pwm_pins', {})
            for pin_key, pin_config in pwm_pins.items():
                if not pin_key.startswith('_') and pin_config.get('enabled', False):
                    used_pins.add(pin_config.get('gpio_pin'))
        
        # Remove None values that might come from missing config
        used_pins.discard(None)
        
        # Filter available pins
        available = {}
        for pin_num, capabilities in cls.GPIO_CAPABILITIES.items():
            # Skip if pin is restricted or already used
            if pin_num in cls.RESTRICTED_PINS or pin_num in used_pins:
                continue
                
            # Only include pins with PWM capability
            if any(cap.startswith('PWM') for cap in capabilities):
                available[pin_num] = capabilities
                
        return available
    
    @classmethod
    def get_pin_display_name(cls, pin_number):
        """
        Get a human-readable display name for a GPIO pin.
        
        Args:
            pin_number (int): GPIO pin number
            
        Returns:
            str: Display name like "GPIO16/PWM0A/SPI0_RX"
        """
        if pin_number not in cls.GPIO_CAPABILITIES:
            return f"GPIO{pin_number} (Unknown)"
            
        capabilities = cls.GPIO_CAPABILITIES[pin_number]
        
        # Format as GPIO<num>/capability1/capability2...
        return "/".join(capabilities)
    
    @classmethod
    def get_pin_options_for_dropdown(cls, exclude_current_usage=True):
        """
        Get formatted pin options suitable for HTML dropdown.
        
        Args:
            exclude_current_usage (bool): If True, exclude pins already configured
            
        Returns:
            list: [(pin_number, display_name), ...] sorted by pin number
        """
        available_pins = cls.get_available_pins(exclude_current_usage)
        
        options = []
        for pin_num in sorted(available_pins.keys()):
            display_name = cls.get_pin_display_name(pin_num)
            options.append((pin_num, display_name))
            
        return options
    
    @classmethod
    def validate_pin_for_pwm(cls, pin_number):
        """
        Validate that a pin can be used for PWM.
        
        Args:
            pin_number (int): GPIO pin number to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not isinstance(pin_number, int):
            return False, "Pin number must be an integer"
            
        if pin_number not in cls.GPIO_CAPABILITIES:
            return False, f"GPIO{pin_number} does not exist on Pico W"
            
        if pin_number in cls.RESTRICTED_PINS:
            return False, cls.RESTRICTED_PINS[pin_number]
            
        capabilities = cls.GPIO_CAPABILITIES[pin_number]
        if not any(cap.startswith('PWM') for cap in capabilities):
            return False, f"GPIO{pin_number} does not support PWM"
            
        # Check if pin is already used for I2C (get from config)
        config = config_manager.get_config_dict()
        hardware = config.get('hardware', {})
        
        rtc_sda_pin = hardware.get('rtc_i2c_sda_pin')
        rtc_scl_pin = hardware.get('rtc_i2c_scl_pin')
        
        if pin_number == rtc_sda_pin:
            return False, f"GPIO{pin_number} is configured as RTC I2C SDA pin"
            
        if pin_number == rtc_scl_pin:
            return False, f"GPIO{pin_number} is configured as RTC I2C SCL pin"
            
        return True, "Pin is valid for PWM use"
    
    @classmethod
    def get_pwm_channel(cls, pin_number):
        """
        Get the PWM channel for a given GPIO pin.
        
        Args:
            pin_number (int): GPIO pin number
            
        Returns:
            str: PWM channel (e.g., "PWM0A") or None if no PWM capability
        """
        if pin_number not in cls.GPIO_CAPABILITIES:
            return None
            
        capabilities = cls.GPIO_CAPABILITIES[pin_number]
        for cap in capabilities:
            if cap.startswith('PWM'):
                return cap
                
        return None


# Create global instance for easy access
gpio_utils = GPIOUtils()
