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

### Hardware
- Raspberry Pi Pico W with MicroPython firmware
- DS3231 RTC module (Real-Time Clock with battery backup)
- LED lighting setup (12V/24V LED strips or individual LEDs)
- MOSFET or LED driver for PWM control (if using high-power LEDs)
- Breadboard or PCB for connections
- Jumper wires
- Power supply for LEDs (if different from Pico W)

### Software
- MicroPython firmware installed on Pico W
- WiFi connection for NTP time sync

## Installation

1. Clone this repository to your local machine.
2. **Copy `config.json.sample` to `config.json`** and update it with your WiFi credentials, timezone offset/name, I2C pins, and other settings.
3. Copy all files to your Raspberry Pi Pico W.
4. Connect and configure hardware as described.
5. Boot the Pico W; the system will connect to WiFi, sync time, and start LED control.

## Hardware Setup

### Wiring Diagram

```
                    Raspberry Pi Pico W
                   ┌─────────────────────┐
               3V3 │1                 40│ VBUS (5V)
               GP0 │2                 39│ VSYS
               GP1 │3                 38│ GND  ────────┐
               GND │4                 37│ 3V3_EN       │
               GP2 │5                 36│ 3V3          │
               GP3 │6                 35│ ADC_VREF     │
               GP4 │7                 34│ GP28         │
               GP5 │8                 33│ AGND         │
               GND │9                 32│ GP27         │
               GP6 │10                31│ GP26         │
               GP7 │11                30│ RUN          │
               GP8 │12                29│ GP22         │
               GP9 │13                28│ GND          │
              GP10 │14                27│ GP21 (SCL) ──┼─── DS3231 SCL
              GP11 │15                26│ GP20 (SDA) ──┼─── DS3231 SDA
              GP12 │16                25│ GP19         │
              GP13 │17                24│ GP18         │
              GND │18                23│ GND          │
              GP14 │19                22│ GP17         │
              GP15 │20                21│ GP16 (PWM) ──┼─── LED Control
                   └─────────────────────┘              │
                                                        │
                DS3231 RTC Module                       │
               ┌─────────────────┐                      │
           VCC │ ●             ● │ VCC (3.3V) ──────────┤
           GND │ ●             ● │ GND ──────────────────┤
           SDA │ ●             ● │ SDA (GP20)           │
           SCL │ ●             ● │ SCL (GP21)           │
               └─────────────────┘                      │
                                                        │
                LED Control Circuit                     │
               ┌─────────────────────────────────────────┘
               │
               │    ┌── LED Strip +12V/24V
               │    │
               │    ▼
           ┌───┴────────┐     ┌─────────┐
           │   MOSFET   │     │ LED     │
     PWM ──┤ (or Driver)├─────┤ Strip/  │
           │            │     │ LEDs    │
           └────┬───────┘     └─────────┘
                │                   │
              ──┴── GND ─────────────┘
               
```

### Connection Details

#### DS3231 RTC Module
| DS3231 Pin | Pico W Pin | Description |
|------------|------------|--------------|
| VCC        | 3V3 (Pin 36) | 3.3V Power |
| GND        | GND (Pin 38) | Ground |
| SDA        | GP20 (Pin 26) | I2C Data Line |
| SCL        | GP21 (Pin 27) | I2C Clock Line |

**Notes:**
- The DS3231 module includes a CR2032 battery for time backup when power is lost
- Some modules have pull-up resistors built-in; if not, add 4.7kΩ resistors between SDA/SCL and 3.3V
- The module operates at 3.3V, perfect for direct connection to Pico W

#### LED Control Output
| Function | Pico W Pin | Wire Color (Suggested) | Description |
|----------|------------|------------------------|-------------|
| PWM Signal | GP16 (Pin 21) | Yellow/Orange | PWM control signal |
| Ground | GND (Pin 38) | Black | Ground reference |
| Power (Optional) | VBUS (Pin 40) | Red | 5V for low-power LEDs |

### LED Driver Circuit Options

#### Option 1: Low-Power LEDs (≤100mA)
```
Pico GP16 (PWM) ────[220Ω]──── LED(s) ────[GND]
                                 │
                               [GND]
```

#### Option 2: High-Power LED Strips (>100mA)
```
Pico GP16 (PWM) ───[1kΩ]──── MOSFET Gate
                                 │
                                 │
                                 │
    LED_SUPPLY_+ ───────────────┼──── LED Strip +
                                 │
                               MOSFET
                               Drain/Source
                                 │
    GND ─────────────────────────┼──── LED Strip -
                                 │
    Pico GND ────────────────────┘
```

**Recommended MOSFETs:**
- **IRF520** (TO-220 package, easy to breadboard)
- **IRLZ44N** (Logic-level, efficient for 3.3V control)
- **2N7000** (Small signal, for moderate currents)

### Power Considerations

#### Pico W Power
- **Operating Voltage**: 5V via USB or 1.8-5.5V via VSYS
- **Current Consumption**: ~100mA (WiFi active), ~20mA (deep sleep)
- **GPIO Output**: 3.3V, max 16mA per pin

#### LED Power
- **Low Power**: Use Pico's 5V (VBUS) for ≤500mA total
- **High Power**: External 12V/24V supply with MOSFET control
- **Current Limiting**: Always use appropriate resistors or current-limited drivers

### Safety Notes
⚠️ **Important Safety Guidelines:**
- Never exceed GPIO current limits (16mA per pin, 50mA total)
- Use appropriate fuses for high-power LED circuits
- Ensure proper heat dissipation for MOSFETs under load
- Double-check polarity before applying power
- Use insulated connectors for AC-powered LED drivers

### Testing Your Setup
1. **Power On**: Pico should show activity LED and connect to WiFi
2. **RTC Check**: System logs should show successful RTC initialization  
3. **LED Test**: Use web interface to manually set different brightness levels
4. **Time Sync**: Verify system displays correct local time in web interface
5. **Automatic Operation**: Let system run through time window changes

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
