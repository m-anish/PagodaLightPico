---
description: Repository Information Overview
alwaysApply: true
---

# PagodaLightPico Information

## Summary
A MicroPython-based LED lighting controller for the Dhamma Laddha Vipassana meditation center's pagoda and meditation cells, powered by the Raspberry Pi Pico W. This project enables precise PWM control of LED lighting, synchronized timekeeping with DS3231 RTC, and network time updates via NTP for serene and energy-efficient ambiance management.

## Structure
- **lib/**: Core library modules for system functionality
  - **umqtt/**: MQTT client implementation for notifications
  - Various utility modules for WiFi, RTC, PWM control, etc.
- **main.py**: Application entry point and main control loop
- **config.json**: Runtime configuration (created from sample)
- **Documentation**: Multiple markdown files for setup and usage

## Language & Runtime
**Language**: MicroPython
**Version**: Compatible with latest MicroPython firmware for Raspberry Pi Pico W
**Build System**: N/A (interpreted language)
**Package Manager**: N/A (manual file deployment)

## Dependencies
**Hardware Dependencies**:
- Raspberry Pi Pico W with MicroPython firmware
- DS3231 RTC module (Real-Time Clock with battery backup)
- LED lighting setup (12V/24V LED strips or individual LEDs)
- MOSFET or LED driver for PWM control

**Software Dependencies**:
- MicroPython standard libraries
- Custom modules in lib/ directory:
  - config_manager.py: JSON configuration management
  - rtc_module.py: DS3231 RTC interface
  - pwm_control.py: LED brightness control
  - web_server.py: Configuration web interface
  - wifi_connect.py: Network connectivity
  - mqtt_notifier.py: Remote notifications

## Build & Installation
```bash
# 1. Install MicroPython firmware on Pico W
# 2. Copy all project files to Pico W
cp -r * /path/to/pico/

# 3. Create configuration file from sample
cp config.json.sample config.json

# 4. Edit configuration with your settings
nano config.json

# 5. Reset Pico W to start the application
```

## Hardware Setup
**RTC Connection**:
- DS3231 VCC → Pico 3V3 (Pin 36)
- DS3231 GND → Pico GND (Pin 38)
- DS3231 SDA → Pico GP20 (Pin 26)
- DS3231 SCL → Pico GP21 (Pin 27)

**LED Control**:
- Default PWM output on GP16 (Pin 21)
- Additional PWM pins configurable in config.json
- MOSFET driver circuit required for high-power LEDs

## Configuration
**Main Configuration File**: config.json
**Format**: JSON with schema validation
**Key Settings**:
- WiFi credentials and hostname
- Timezone settings
- Hardware pin assignments
- PWM frequency
- Time windows for lighting control
- MQTT notification settings

**Web Interface**:
- Available at http://[pico-ip]/ when WiFi connected
- Real-time configuration updates
- Visual time window editor

## System Components
**Main Application Flow**:
1. Initialize WiFi and connect to network
2. Sync time from NTP and update RTC
3. Start web server for configuration
4. Connect to MQTT broker if enabled
5. Enter main loop:
   - Handle web requests
   - Check for configuration changes
   - Update PWM outputs based on time windows
   - Send status notifications

**Time Management**:
- NTP synchronization when WiFi available
- DS3231 RTC for offline timekeeping
- Dynamic sunrise/sunset calculation for Leh, India
- Time window system for scheduled lighting changes

**LED Control**:
- PWM-based brightness control (0-100%)
- Multiple independent channels
- Time-based automatic adjustment
- Manual override via web interface