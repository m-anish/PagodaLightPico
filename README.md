# PagodaLightPico

A MicroPython-based LED lighting controller for the Dhamma Laddha Vipassana meditation center’s pagoda and meditation cells, powered by the Raspberry Pi Pico W. This project enables precise PWM control of LED lighting, synchronized timekeeping with DS3231 RTC, and network time updates via NTP for serene and energy-efficient ambiance management.

## Features

- WiFi-enabled time synchronization (NTP) on Raspberry Pi Pico W
- DS3231 Real-Time Clock (RTC) integration for accurate local timekeeping
- PWM-controlled LED lighting for pagoda and meditation cells
- **NEW: Web-based configuration interface** for runtime settings updates
- **NEW: JSON configuration system** with live validation and reload
- Modular codebase using MicroPython with hardware abstraction layers
- Robust logging and debug facilities
- Designed for low power and serene environmental control

## Requirements

- Raspberry Pi Pico W
- DS3231 RTC module
- LED lighting setup with PWM control
- MicroPython firmware installed on Pico W
- WiFi connection for NTP time sync

## Installation

1. Clone this repository to your local machine.
2. Copy the contents to your Raspberry Pi Pico W.
3. **Update `config.json`** with your WiFi credentials, timezone offset/name, I2C pins, and other settings.
4. Connect and configure hardware as described.
5. Boot the Pico W; the system will connect to WiFi, sync time, and start LED control.

## Configuration

### JSON Configuration (config.json)
The system now uses JSON-based configuration for easy runtime updates:

- **WiFi Settings**: Network SSID and password
- **Timezone**: Name and UTC offset in hours
- **Hardware**: GPIO pins for RTC I2C and LED PWM, PWM frequency
- **System**: Log level and update interval
- **Time Windows**: LED brightness schedules for different times of day

### Web Configuration Interface
When WiFi is connected, access the configuration interface at:
```
http://[pico-w-ip-address]/
```

The web interface provides:
- 🏯 **Real-time configuration updates** without restarting the system
- 📱 **Mobile-friendly interface** with responsive design
- ✅ **Live validation** of all configuration values
- 🔒 **Automatic backup** of settings to JSON file
- 🌅 **Visual time window editor** for lighting schedules

## Usage

### Basic Operation
- The main script initializes WiFi and RTC, then starts controlling LEDs
- Logs provide detailed status with timestamped entries
- LED brightness automatically adjusts based on configured time windows
- "Day" window is automatically adjusted to sunrise/sunset times for Leh, India

### Configuration Updates
1. **Via Web Interface** (Recommended):
   - Navigate to `http://[pico-ip]/` in your web browser
   - Update any settings using the intuitive web form
   - Changes apply immediately without system restart

2. **Via JSON File**:
   - Edit `config.json` directly
   - Changes are detected and applied on next update cycle

### Time Window Configuration
- **Day Window**: Automatically set to sunrise/sunset (brightness usually 0%)
- **Evening/Night Windows**: Configure custom lighting schedules
- **Overnight Windows**: Support for schedules crossing midnight
- **Brightness Control**: 0-100% PWM duty cycle for each window

## Contributing

Contributions, issues, and feature requests are welcome!  
Feel free to fork the repository and submit pull requests.

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.  
See the [LICENSE](LICENSE) file for details.
