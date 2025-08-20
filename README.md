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

### Software
- MicroPython firmware installed on Pico W
- WiFi connection for NTP time sync

## Installation

1. Clone this repository to your local machine.
2. **Copy `config.json.sample` to `config.json`** and update it with your WiFi credentials, timezone offset/name, I2C pins, and other settings.
3. Copy all files to your Raspberry Pi Pico W.
4. Boot the Pico W; the system will connect to WiFi, sync time, and start LED control.

## Configuration

### JSON Configuration (config.json)
The system now uses JSON-based configuration for easy runtime updates:

- **WiFi Settings**: Network SSID and password
- **Timezone**: Name and UTC offset in hours
- **Hardware**: GPIO pins for RTC I2C and LED PWM, PWM frequency
- **System**: Log level and intervals/tunables
  - `update_interval` (seconds): PWM update cadence. Default: 120
  - `network_check_interval` (seconds): Network monitor cadence. Default: 120
  - `server_idle_sleep_ms` (milliseconds): Web server accept-loop idle backoff. Default: 300
  - `client_read_sleep_ms` (milliseconds): Web server client recv backoff. Default: 50
- **Time Windows**: LED brightness schedules for different times of day

### Web Interface (Async server)
When WiFi is connected, access the web interface at:
```
http://[pico-w-ip-address]/
```

The new Microdot-powered web interface provides:

#### Main Dashboard (`/`)
- 🏛️ **System status overview** with real-time information
- ⏰ **Current time and date** display
- 📡 **Connection status** (WiFi, MQTT, Web Server)
- 💡 **Active PWM pins** summary with configuration details
- 🧭 **Navigation** to configuration and status pages

#### Configuration Page (`/config`)
- ⚙️ **View current configuration** in readable format
- 📋 **JSON configuration display** for technical users
- 🔄 **Future: Real-time editing** capabilities

#### System Status (`/status`)
- 📊 **Detailed system information** and health monitoring
- 🔗 **Connection health** for all network services
- ⏱️ **System uptime** and performance metrics

#### JSON API Endpoints
- `GET /api/config` - Current configuration as JSON
- `GET /api/status` - System status as JSON  
- `GET /api/pins` - PWM pins status as JSON

## Usage

### Basic Operation
- The main script initializes WiFi and RTC, then starts controlling LEDs
- Logs provide detailed status with timestamped entries
- LED brightness automatically adjusts based on configured time windows
- "Day" window is automatically adjusted to sunrise/sunset times from configurable location data

### Configuration Updates
1. **Via Web Interface** (Current):
   - Navigate to `http://[pico-ip]/` for the main dashboard
   - View current configuration at `http://[pico-ip]/config`
   - Monitor system status at `http://[pico-ip]/status`
   - Access JSON APIs for programmatic integration

2. **Via JSON File**:
   - Edit `config.json` directly on the device
   - Changes are detected and applied on next update cycle
   - Use `/api/config` endpoint to verify changes

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

## Notifications (MQTT)
The device can publish JSON events (window changes, errors, system events) to an MQTT broker.

- Public brokers for testing: `broker.hivemq.com`, `test.mosquitto.org`
- Managed free tier (recommended for reliability): EMQX Cloud
- Minimal `config.json` example:
  ```json
  {
    "notifications": {
      "enabled": true,
      "mqtt_broker": "broker.hivemq.com",
      "mqtt_port": 1883,
      "mqtt_topic": "PagodaLightPico/notifications",
      "mqtt_client_id": "PagodaLightPico"
    }
  }
  ```
- Simple bridge (Pushover via Python):
  ```python
  import paho.mqtt.client as mqtt, requests, json
  TOKEN="your_api_token"; USER="your_user_key"
  def on_message(c,u,m):
      try:
          d=json.loads(m.payload.decode());
          requests.post("https://api.pushover.net/1/messages.json",
                      data={"token":TOKEN,"user":USER,
                            "title":"🏯 PagodaLight","message":d.get("message","")})
      except Exception as e:
          print(e)
  cl=mqtt.Client(); cl.on_message=on_message
  cl.connect("broker.hivemq.com",1883,60)
  cl.subscribe("PagodaLightPico/notifications/+")
  cl.loop_forever()
  ```

## Troubleshooting
- **WiFi signal**: Place device near router; avoid interference.
- **Timeouts (ETIMEDOUT)**: Tune network settings in `config.json`:
  Tunable fields (in `system`):
  ```json
  {
    "system": {
      "update_interval": 120,
      "network_check_interval": 120,
      "server_idle_sleep_ms": 300,
      "client_read_sleep_ms": 50
    }
  }
  ```
- **MQTT**: Increase `mqtt_keepalive`/`mqtt_timeout`, prefer stable broker.
- **Memory**: Reduce features (disable notifications), lower web response size, restart if needed.
- **mDNS**: If discovery fails, use IP or ensure multicast is allowed on your network.

## Developer Quickstart
- Copy sample config: `cp config.json.sample config.json`
- Deploy files to Pico W (choose one tool):
  - rshell: `rshell -p /dev/ttyACM0 cp -r . /pyboard/`
  - ampy: `ampy -p /dev/ttyACM0 put lib/ && ampy -p /dev/ttyACM0 put main.py && ampy -p /dev/ttyACM0 put config.json`
- REPL/debug: `rshell -p /dev/ttyACM0 repl` or `screen /dev/ttyACM0 115200`
- After edits: Ctrl+D in REPL for soft reset
- Check memory in REPL: `import gc; gc.collect(); print(gc.mem_free())`
