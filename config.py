"""
Configuration for PagodaLightPico

Rename to config.py before use and set values as needed.
"""

WIFI_SSID = "iPhone"
WIFI_PASSWORD = "this is some key"

TIMEZONE_NAME = "IST"       # e.g., IST, UTC, PST
TIMEZONE_OFFSET = 5.5       # Offset from UTC in hours

RTC_I2C_SDA_PIN = 20       # GPIO pins for I2C (DS3231)
RTC_I2C_SCL_PIN = 21

LED_PWM_PIN = 16           # GPIO pin used for PWM LED control

PWM_FREQUENCY = 1000       # PWM frequency in Hz

LOG_LEVEL = 'DEBUG'        # Logging levels: FATAL, ERROR, WARN, INFO, DEBUG

UPDATE_INTERVAL = 60       # Update interval in seconds; controls frequency of LED updates

# Time windows for LED duty cycle control; "day" window start/end replaced dynamically
TIME_WINDOWS = {
    "day": {
        "start": "06:00",  # Default 6am
        "end": "18:00",    # Default 6pm
        "duty_cycle": 0    # Default duty cycle for day is 0
    },
    "window_1": {
        "start": "18:00",
        "end": "20:00",
        "duty_cycle": 60
    },
    "window_2": {
        "start": "20:00",
        "end": "22:00",
        "duty_cycle": 40
    },
    "window_3": {
        "start": "22:00",
        "end": "00:00",
        "duty_cycle": 20
    },
    "window_4": {
        "start": "00:00",
        "end": "04:00",
        "duty_cycle": 10
    },
    "window_5": {
        "start": "04:00",
        "end": "06:00",
        "duty_cycle": 30
    }
}
