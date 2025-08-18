# PagodaLightPico

A MicroPython-based LED lighting controller for the Dhamma Laddha Vipassana meditation center’s pagoda and meditation cells, powered by the Raspberry Pi Pico W. This project enables precise PWM control of LED lighting, synchronized timekeeping with DS3231 RTC, and network time updates via NTP for serene and energy-efficient ambiance management.

## Features

- WiFi-enabled time synchronization (NTP) on Raspberry Pi Pico W
- DS3231 Real-Time Clock (RTC) integration for accurate local timekeeping
- PWM-controlled LED lighting for pagoda and meditation cells
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
3. **Rename `config.py.sample` to `config.py`** and update it with your WiFi credentials, timezone offset/name, I2C pins, and logging level.
4. Connect and configure hardware as described.
5. Boot the Pico W; the system will connect to WiFi, sync time, and start LED control.

## Configuration

- Set your WiFi SSID and password in `config.py`.
- Set your timezone offset and name (e.g., IST, UTC+5:30) in `config.py`.
- Adjust PWM parameters and LED pins as needed in the code.

## Usage

- The main script initializes WiFi and RTC, then starts controlling LEDs based on your settings.
- Logs provide detailed status with timestamped entries.
- Modify or extend the code to customize light behavior or add features.

## Contributing

Contributions, issues, and feature requests are welcome!  
Feel free to fork the repository and submit pull requests.

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.  
See the [LICENSE](LICENSE) file for details.
