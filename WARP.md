# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

PagodaLightPico is a **MicroPython-based LED lighting controller** for Raspberry Pi Pico W that manages meditation center lighting. It runs entirely on the microcontroller with no traditional build process - files are copied directly to the device.

## Development Commands

### Device Setup and Deployment
```bash
# Copy configuration sample to working config (first time setup)
cp config.json.sample config.json

# Copy all files to Pico W (using rshell, ampy, or Thonny)
rshell -p /dev/ttyACM0 cp -r . /pyboard/
# OR using ampy
ampy -p /dev/ttyACM0 put lib/
ampy -p /dev/ttyACM0 put main.py
ampy -p /dev/ttyACM0 put config.json

# Connect to device REPL for debugging
rshell -p /dev/ttyACM0 repl
# OR using screen/picocom
screen /dev/ttyACM0 115200
```

### Development and Debugging
```bash
# Monitor device logs in real-time via REPL
rshell -p /dev/ttyACM0 repl

# Restart main program after file changes
# In REPL: Ctrl+D (soft reset) or Ctrl+C then run main.py

# Check device file system
rshell -p /dev/ttyACM0 ls /pyboard/

# Remove files from device (cleanup)
rshell -p /dev/ttyACM0 rm /pyboard/main.py
```

### Configuration Management
```bash
# Edit local config and sync to device
editor config.json
ampy -p /dev/ttyACM0 put config.json

# Access web interface (when WiFi connected)
# Navigate to: http://[pico-ip-address]/
# Get IP from device logs or router DHCP table
```

### MicroPython-Specific Development
```bash
# Install MicroPython packages (if needed)
# Note: This project uses only built-in libraries

# Check MicroPython memory usage in REPL:
# import gc; gc.collect(); print("Free:", gc.mem_free())

# View device information in REPL:
# import machine; print("Unique ID:", machine.unique_id())
```

## Architecture Overview

### Core System Architecture
The system uses a **modular, hardware-abstracted architecture** with these key components:

- **Configuration Layer**: JSON-based runtime configuration with web interface
- **Hardware Abstraction**: Separate modules for RTC, PWM, WiFi, and MQTT
- **Time Management**: DS3231 RTC integration with NTP synchronization and timezone handling
- **Lighting Control**: Dynamic time-window based PWM control with sunrise/sunset calculation
- **Network Services**: Built-in web server for configuration and MQTT for notifications

### Module Dependencies
```
main.py (entry point)
├── config_manager.py (configuration management)
├── web_server.py (HTTP configuration interface)
├── wifi_connect.py (network connectivity)
├── rtc_module.py (DS3231 RTC interface)
├── pwm_control.py (LED PWM control)
├── mqtt_notifier.py (push notifications)
├── sun_times.py (sunrise/sunset calculations)
├── system_status.py (system state management)
└── simple_logger.py (timestamped logging)
```

### Key Architectural Patterns

**Configuration Management**: 
- JSON-based configuration with runtime updates via web interface
- Backward compatibility layer for old config.py format
- Live validation and automatic reloading

**Time Window System**:
- Dynamic sunrise/sunset calculation for "day" window
- Support for overnight windows crossing midnight
- Configurable brightness levels per window

**Hardware Abstraction**:
- PWM controller with frequency and duty cycle management
- I2C RTC communication through shared rtc instance
- WiFi connection with retry logic and hostname configuration

**Web Interface Architecture**:
- Simple HTTP server with routing table
- Memory-efficient request handling with chunked responses
- JSON API endpoints alongside HTML forms

## Development Patterns

### Adding New Time Windows
1. Update `config.json` time_windows section with new window definition
2. The system automatically detects and applies new windows without code changes
3. Test via web interface at `http://[pico-ip]/windows`

### Extending Hardware Support
1. Add new hardware module in `lib/` directory
2. Import and initialize in `main.py`
3. Add configuration parameters to `config_manager.py`
4. Update validation logic in `_validate_config()`

### Adding Notification Types
1. Extend `mqtt_notifier.py` with new notification method
2. Add configuration options to notifications section
3. Call notification method from appropriate system events

### Memory Management
- Use `gc.collect()` before memory-intensive operations
- Minimize large string concatenations in web responses
- Monitor memory usage with `gc.mem_free()` during development

### Error Handling Patterns
- Graceful degradation: system continues with reduced functionality on errors
- Error logging with timestamps through `simple_logger.py`
- LED status indicators for connection states
- MQTT error notifications when available

## Configuration Structure

The system uses JSON configuration with these main sections:
- `wifi`: Network credentials and hostname
- `timezone`: Local timezone settings (name and UTC offset)
- `hardware`: GPIO pin assignments and PWM frequency
- `system`: Logging level and update intervals
- `notifications`: MQTT broker settings for push notifications
- `time_windows`: Brightness schedules for different times of day

## Hardware Interface

**Required Hardware**:
- Raspberry Pi Pico W with MicroPython firmware
- DS3231 RTC module (I2C connection on pins 20/21)
- LED control circuit (PWM output on pin 16)
- Power supply appropriate for LED load

**Pin Configuration** (customizable via config):
- GPIO 20: RTC I2C SDA
- GPIO 21: RTC I2C SCL  
- GPIO 16: LED PWM output
- GPIO 25: Built-in LED (connection status)

## Debugging and Troubleshooting

**Common Issues**:
- WiFi connection failures: Check credentials in config.json
- Time sync issues: Verify NTP access and timezone settings
- Memory errors: Monitor with `gc.mem_free()`, optimize web responses
- RTC communication: Check I2C connections and address

**Debugging Tools**:
- REPL access via USB for real-time debugging
- Web interface provides system status and memory usage
- Structured logging with timestamps and levels
- MQTT notifications for remote error monitoring

**Log Analysis**:
- Timestamps include timezone information
- Log levels: FATAL, ERROR, WARN, INFO, DEBUG
- Module-specific log prefixes (e.g., [WEB], [MQTT], [NTP])
