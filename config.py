"""
Configuration constants for the PWM controller project.

Includes settings for PWM output, time zone, RTC I2C pins,
WiFi credentials, and logging level.
"""

PWM_PIN = 15            # GPIO pin used for PWM output
PWM_FREQ = 500          # PWM frequency in Hz (default)

TIMEZONE_OFFSET = 5.5   # IST offset from UTC in hours
TIMEZONE_NAME = "IST"

# RTC I2C pins
RTC_I2C_SDA_PIN = 20    # GPIO pin for I2C SDA
RTC_I2C_SCL_PIN = 21    # GPIO pin for I2C SCL

# WiFi credentials
WIFI_SSID = "iPhone"
WIFI_PASSWORD = "this is some key"

# Logging level (FATAL, ERROR, WARN, INFO, DEBUG)
LOG_LEVEL = "DEBUG"
