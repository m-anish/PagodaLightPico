# PagodaLightPico

A MicroPython-based LED lighting controller for the Dhamma Laddha Vipassana meditation center’s pagoda and meditation cells, powered by the Raspberry Pi Pico W. This project enables precise PWM control of LED lighting, synchronized timekeeping with DS3231 RTC, and network time updates via NTP for serene and energy-efficient ambiance management.

## Features

- WiFi-enabled time synchronization (NTP) on Raspberry Pi Pico W
- DS3231 Real-Time Clock (RTC) integration for accurate local timekeeping
- PWM-controlled LED lighting for pagoda and meditation cells
- **NEW: Web-based configuration interface** for runtime settings updates
- **NEW: JSON configuration system** with live validation and reload
- **NEW (0.4.1): Streaming upload pages** for `config.json` and `sun_times.json` with chunked uploads for low RAM usage on Pico W
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
3. **Copy `sun_times.json.sample` to `sun_times.json`** and adjust for your location (latitude/longitude) and local sunrise/sunset times.
4. Copy all files to your Raspberry Pi Pico W.
5. Boot the Pico W; the system will connect to WiFi, sync time, and start LED control.

## Configuration

### JSON Configuration (config.json)
The system now uses JSON-based configuration for easy runtime updates:

- **WiFi Settings**: Network SSID and password
- **Timezone**: Name and UTC offset in hours
- **Hardware**: GPIO pins for RTC I2C and LED PWM, PWM frequency
- **System**: Log level and intervals/tunables
- **Version**: Set `version` (e.g., `0.2.0`).
  - The web UI enforces that the uploaded file's major.minor (e.g., `0.2`) must match the device's running config version's major.minor.
  - If the running config has no valid semantic version (missing or not like `X.Y.Z`), uploads are rejected with a hard error until `config.json` is fixed.
  - Both `config.json` and `sun_times.json` must include a `version` field and follow the same major.minor matching rule.
  - `update_interval` (seconds): PWM update cadence. Default: 120
  - `network_check_interval` (seconds): Network monitor cadence. Default: 120
  - `server_idle_sleep_ms` (milliseconds): Web server accept-loop idle backoff. Default: 300
  - `client_read_sleep_ms` (milliseconds): Web server client recv backoff. Default: 50
- **Time Windows**: LED brightness schedules for different times of day

#### Ordering helper keys (UI-only)
- Keys beginning with `_` are ignored by firmware logic but can be used by tools/UI.
- You may include:
  - A numeric `_order` inside each window object (e.g., `"day": { ..., "_order": 1 }`) to hint display order.
  - A top-level `_order` array within `time_windows` that lists window names in order, e.g.:
    ```json
    "time_windows": {
      "_order": ["day", "evening", "night"],
      "day": { "start": "sunrise", "end": "sunset", "duty_cycle": 0 },
      "evening": { "start": "sunset", "end": "22:00", "duty_cycle": 60 },
      "night": { "start": "22:00", "end": "sunrise", "duty_cycle": 20 }
    }
    ```
  - Ordering is for display only; the device selects a window by checking the current time against each window (keys starting with `_` are ignored).

### Web Interface (Async server)
When WiFi is connected, access the web interface at:
```
http://[pico-w-ip-address]/
```

The new Microdot-powered web interface provides:

#### Main Dashboard (`/`)
- 🏛️ **System status overview** with real-time information
- ⏰ **Current time and date** display
- 🧾 **Config version display** (shows current `config.json` version)
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

#### Upload Pages (0.4.1)
- `GET /upload-config` — Streamed HTML page to upload a new `config.json` in 1KB chunks.
- `GET /upload-sun-times` — Streamed HTML page to upload a new `sun_times.json` in 1KB chunks.
- Uploads use chunked endpoints to reduce RAM usage on Pico W. On success, the device applies the new file (config may require a soft reboot).

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

### Testing MQTT Notifications

This guide helps you quickly test the device’s MQTT notifications end-to-end.

#### 1) Choose a free broker
- Public, no signup (fastest): `broker.hivemq.com:1883`, `test.mosquitto.org:1883`
- Managed free tier (more reliable, signup required): EMQX Cloud

For a quick test, use HiveMQ Public (`broker.hivemq.com:1883`). Topics are public—use unique topic/client IDs.

#### 2) Configure the device (`config.json`)
Set the `notifications` block (keys read by `lib/mqtt_notifier.py` and `lib/config_manager.py`):

```json
{
  "notifications": {
    "enabled": true,
    "mqtt_broker": "broker.hivemq.com",
    "mqtt_port": 1883,
    "mqtt_topic": "PagodaLightPico/notifications/your-unique-suffix",
    "mqtt_client_id": "PagodaLightPico-your-unique-suffix",
    "notify_on_window_change": true,
    "notify_on_errors": true
  }
}
```

The notifier publishes to:
- `.../system` (startup/shutdown)
- `.../pin_change` (individual pin window changes)
- `.../summary` (multi-pin summary)
- `.../error` (errors)
- `.../config` (config updates)

#### 3) Subscribe on your computer (Linux)
Option A: mosquitto-clients
```bash
sudo apt-get install -y mosquitto-clients
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'PagodaLightPico/notifications/your-unique-suffix/#' -v
```

Option B: Python (paho-mqtt)
```python
import json
import paho.mqtt.client as mqtt

TOPIC = "PagodaLightPico/notifications/your-unique-suffix/#"

def on_connect(client, userdata, flags, rc):
    print("Connected rc=", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        print(msg.topic, json.loads(msg.payload.decode()))
    except Exception:
        print(msg.topic, msg.payload.decode())

client = mqtt.Client(client_id="PC-Subscriber-your-unique-suffix")
client.on_connect = on_connect
client.on_message = on_message
client.connect("broker.hivemq.com", 1883, 60)
client.loop_forever()
```

#### 4) Trigger device messages
- On boot and successful MQTT connect, the device publishes a `system_startup` event to `.../system` (see `main.py` calling `mqtt_notifier.connect()`).
- Window/duty changes publish to `.../pin_change` via `update_pwm_pins()`.

Tips to see activity quickly:
- Temporarily set `system.update_interval` low (e.g., `10`) in `config.json`.
- Adjust one pin’s time windows or duty cycles around “now”. Ensure at least one pin is enabled.

#### 5) Optional: sanity-check with a publish from PC
```bash
mosquitto_pub -h broker.hivemq.com -p 1883 \
  -t 'PagodaLightPico/notifications/your-unique-suffix/test' \
  -m '{"hello":"world"}'
```
You should see this in your subscriber.

#### 6) Mobile viewing (optional)
Use an MQTT app (e.g., MQTT Dash on Android), connect to `broker.hivemq.com:1883`, and subscribe to `PagodaLightPico/notifications/your-unique-suffix/#`.

#### Notes
- Public brokers are plaintext; don’t publish secrets.
- Use unique topics/client IDs to avoid cross-traffic.
- For TLS/reliability (e.g., EMQX Cloud), you’ll need SSL settings. The bundled `umqtt.simple` supports SSL, but `MQTTNotifier.connect()` currently doesn’t pass `ssl=True`. Open an issue if you want SSL wired up in code.

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
- Copy sample sun times: `cp sun_times.json.sample sun_times.json`
- Deploy files to Pico W (choose one tool):
  - rshell: `rshell -p /dev/ttyACM0 cp -r . /pyboard/`
  - ampy: `ampy -p /dev/ttyACM0 put lib/ && ampy -p /dev/ttyACM0 put main.py && ampy -p /dev/ttyACM0 put config.json && ampy -p /dev/ttyACM0 put sun_times.json`
- REPL/debug: `rshell -p /dev/ttyACM0 repl` or `screen /dev/ttyACM0 115200`
- After edits: Ctrl+D in REPL for soft reset
- Check memory in REPL: `import gc; gc.collect(); print(gc.mem_free())`

## Automated GitHub Pages deployment and Auto-merge

The helper app in `helper-app/` is deployed to GitHub Pages via the workflow at `.github/workflows/gh-pages.yml`.

- The site deploys automatically on pushes to the default branch (`main`/`master`).
- For feature branches, open a Pull Request. You can automate merging with the "automerge" label.

### Auto-merge PRs with the "automerge" label

We use `.github/workflows/auto-merge.yml` to merge PRs labeled `automerge` after all checks pass.

Steps:
1. Create a PR targeting `main`.
2. Add the label `automerge` to the PR.
3. Wait for required checks to pass. The workflow will squash-merge the PR automatically.
4. Merge to `main` triggers the Pages deploy workflow which publishes the latest `helper-app/` and includes `config.json.sample` and `sun_times.json.sample` at the site root.

Recommended repo settings:
- Settings → Branches → Protect `main` with required status checks (e.g., "Deploy helper app to GitHub Pages").
- Settings → Pages → Build and deployment → Source = "GitHub Actions".
