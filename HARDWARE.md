# PagodaLight Hardware Documentation

This document provides detailed hardware setup instructions, wiring diagrams, and troubleshooting information for the PagodaLight system.

## Bill of Materials (BOM)

### Essential Components
| Component | Quantity | Specifications | Purpose |
|-----------|----------|----------------|---------|
| Raspberry Pi Pico W | 1 | With headers soldered | Main controller with WiFi |
| DS3231 RTC Module | 1 | I2C, with CR2032 battery | Real-time clock backup |
| LED Strip/Array | 1+ | 12V/24V, PWM compatible | Lighting elements |
| MOSFET | 1+ | Logic-level, appropriate current | LED driver for high power |
| Resistors | Various | 220Ω, 1kΩ, 4.7kΩ | Current limiting, pull-ups |
| Breadboard/PCB | 1 | Half-size minimum | Prototyping platform |
| Jumper Wires | 10+ | Male-Male, Male-Female | Connections |
| Power Supply | 1 | Match LED voltage/current | LED power |

### Optional Components
| Component | Quantity | Specifications | Purpose |
|-----------|----------|----------------|---------|
| Capacitors | 2-4 | 100µF, 0.1µF | Power filtering |
| Fuse | 1 | Match LED current | Overcurrent protection |
| Terminal Blocks | 2-4 | Screw terminals | Secure connections |
| Enclosure | 1 | IP65 rated (outdoor use) | Weather protection |

## Detailed Wiring Instructions

### Step 1: Prepare the Pico W
1. **Install MicroPython**: Download latest firmware from [micropython.org](https://micropython.org/download/rp2-pico-w/)
2. **Connect via USB**: Hold BOOTSEL button while plugging in
3. **Flash firmware**: Copy .uf2 file to RPI-RP2 drive
4. **Test connection**: Use Thonny IDE or similar to verify operation

### Step 2: Connect DS3231 RTC Module

```
DS3231 RTC Module Pinout:
┌─────────────────┐
│ VCC  GND  SDA  SCL │ ← Standard layout
│  ●    ●    ●    ●  │
│                    │
│   DS3231 MODULE    │
│                    │
│  32kHz  SQW  RST   │ ← Additional pins (optional)
│   ●     ●    ●     │
└─────────────────┘
```

**Connection Steps:**
1. **Power (VCC to 3V3)**: Red wire from DS3231 VCC to Pico pin 36 (3V3)
2. **Ground (GND to GND)**: Black wire from DS3231 GND to Pico pin 38 (GND)  
3. **Data (SDA to GP20)**: Blue/Green wire from DS3231 SDA to Pico pin 26 (GP20)
4. **Clock (SCL to GP21)**: Yellow/White wire from DS3231 SCL to Pico pin 27 (GP21)

**Pull-up Resistors:**
- Most DS3231 modules include 4.7kΩ pull-up resistors
- If your module doesn't have them, add between SDA/SCL and 3.3V
- Check with multimeter: resistance between SDA/VCC should be ~4.7kΩ

### Step 3: LED Control Circuit

#### For Low-Power LEDs (<100mA total)

```
Simple Direct Drive Circuit:

Pico GP16 ────[220Ω]────●────LED1────┐
                        │             │
                    [220Ω]       [220Ω]
                        │             │
                      LED2          LED3
                        │             │
                        └─────┬───────┘
                              │
                            GND
```

**Component Selection:**
- **Resistor Value**: R = (Vsupply - VLED) / ILED
- **Example**: For 3.3V supply, 2V LED, 10mA: R = (3.3-2)/0.01 = 130Ω (use 150Ω)

#### For High-Power LED Strips (>100mA)

```
MOSFET Driver Circuit:

                    LED Strip Power Supply
                           │ +12V/24V
                           ▼
                    ┌─────────────┐
                    │ LED Strip + │
                    └──────┬──────┘
                           │
                           │ 
    Pico GP16 ──[1kΩ]──┬──┤ Drain
                        │  │
                   [10kΩ]  │ MOSFET
                        │  │ (IRF520)
                      GND   │ Source
                           │
                           ├── LED Strip -
                           │
                         GND ── Power Supply -
```

**MOSFET Selection Guide:**
| MOSFET | VDS | RDS(on) | ID | Package | Use Case |
|--------|-----|---------|----|---------|-----------| 
| IRF520 | 100V | 0.27Ω | 9.7A | TO-220 | General purpose |
| IRLZ44N | 55V | 0.022Ω | 47A | TO-220 | High current |
| 2N7000 | 60V | 5.3Ω | 0.2A | TO-92 | Low current |
| IRL540N | 100V | 0.077Ω | 22A | TO-220 | Medium current |

### Step 4: Power Distribution

#### Power Requirements Calculation
```
System Power Budget:
- Pico W (WiFi active): ~100mA @ 5V = 0.5W
- DS3231 RTC: ~3mA @ 3.3V = 0.01W  
- LED Strip: Varies (check specifications)

Example 5m LED strip (60 LEDs/m, 5050 type):
- Maximum: 300 LEDs × 60mA = 18A @ 12V = 216W
- At 50% PWM: ~108W
- Power supply needed: 12V, 20A minimum
```

#### Power Supply Options
1. **USB Power (Pico only)**: 5V, 500mA maximum
2. **External 5V**: For low-power LED setups
3. **12V/24V + Buck Converter**: For high-power systems
4. **Dual Supply**: Separate supplies for logic and LEDs

### Step 5: Assembly and Testing

#### Breadboard Layout
```
Breadboard Connection Layout:

                    Power Rails
                 + ═══════════ - 
                 │             │
    Components   │             │   Components
    Section  ────┼─────────────┼──── Section
                 │             │
                 │   Pico W    │
                 │  (center)   │  
                 │             │
                 + ═══════════ - 
                    Power Rails
```

**Assembly Steps:**
1. **Place Pico W**: Center of breadboard, pins in different rows
2. **Connect power rails**: 3.3V and GND to both sides
3. **Add DS3231**: Near Pico, short wire connections
4. **Build LED circuit**: On one side, away from logic
5. **Add filtering**: 0.1µF cap near Pico VCC/GND

#### Testing Procedure
1. **Visual Inspection**: Check all connections before power
2. **Power Test**: Measure voltages at key points
3. **I2C Test**: Scan for DS3231 address (0x68)
4. **LED Test**: Manual PWM control via web interface
5. **System Test**: Full time-based operation

## Troubleshooting Guide

### Common Issues

#### Pico W Won't Connect to WiFi
- **Check credentials**: Verify SSID/password in config.json
- **Signal strength**: Move closer to router
- **Power supply**: Ensure stable 5V supply
- **Antenna**: Check onboard antenna is not damaged

#### RTC Not Working
```bash
# Test I2C connection (run on Pico):
import machine
i2c = machine.I2C(0, sda=machine.Pin(20), scl=machine.Pin(21))
print(i2c.scan())  # Should show [104] (0x68 in decimal)
```
- **No response**: Check wiring, power, pull-up resistors
- **Wrong time**: Battery may be dead, replace CR2032
- **Intermittent**: Poor connections, re-solder if needed

#### LEDs Not Working
- **No output**: Check PWM pin assignment in config
- **Dim/flickering**: Insufficient power supply
- **No control**: MOSFET may be damaged or wrong type
- **Overheating**: Add heat sink to MOSFET

#### Web Interface Issues
- **Can't access**: Check IP address with `ipconfig` command
- **Slow response**: Reduce web request frequency
- **Configuration not saving**: Check file system permissions

### Advanced Diagnostics

#### Power Analysis
```python
# Measure system current (add to main.py for testing):
import time
import machine

# Monitor power consumption
def power_test():
    # LED off
    pwm.duty_u16(0)
    time.sleep(5)
    print("LED OFF - measure current now")
    
    # LED 50%
    pwm.duty_u16(32767)
    time.sleep(5)
    print("LED 50% - measure current now")
    
    # LED 100%
    pwm.duty_u16(65535)
    time.sleep(5)
    print("LED 100% - measure current now")
```

#### Signal Analysis
- **Oscilloscope**: Check PWM frequency and duty cycle
- **Logic Analyzer**: Verify I2C communications
- **Multimeter**: Measure voltages and currents

## PCB Design Considerations

### Layout Guidelines
1. **Separate analog/digital**: Keep PWM traces away from I2C
2. **Ground plane**: Solid ground connection for noise immunity
3. **Power filtering**: Place caps close to ICs
4. **Heat dissipation**: Thermal vias under MOSFETs
5. **Protection**: ESD protection on exposed pins

### Schematic Symbols
```
Standard component symbols used:
- μC: Microcontroller (Pico W)
- RTC: Real-time clock (DS3231)  
- Q: MOSFET transistor
- R: Resistor
- C: Capacitor
- J: Connector/Jack
- LED: Light emitting diode
```

## Safety and Compliance

### Electrical Safety
- **Low Voltage**: Keep control circuits \u003c50V
- **Isolation**: Isolate high-power LED circuits
- **Fusing**: Always fuse the power supply
- **Grounding**: Proper earth ground for metal enclosures

### Environmental Considerations
- **IP Rating**: IP65 minimum for outdoor installations
- **Temperature**: Operating range -10°C to +50°C
- **Humidity**: Conformal coating for high humidity
- **UV Protection**: UV-rated materials for sun exposure

### Regulatory
- **CE/FCC**: May require certification for commercial use
- **RoHS**: Use lead-free components
- **Electrical Code**: Follow local electrical installation codes

## Maintenance

### Regular Checks
- **Monthly**: Visual inspection, LED operation test
- **Quarterly**: RTC battery voltage check
- **Annually**: Deep clean, connector re-seating

### Component Lifespans
- **Pico W**: 10+ years (no moving parts)
- **DS3231**: 10+ years (crystal aging \u003c2ppm/year)
- **CR2032**: 3-5 years (depends on usage)
- **LEDs**: 50,000+ hours (depends on quality)
- **MOSFETs**: 10+ years (if not overstressed)

### Replacement Procedures
1. **Power down system**: Always disconnect power first
2. **Document settings**: Export config via web interface
3. **Replace component**: Use same specifications
4. **Test thoroughly**: Full system verification
5. **Update documentation**: Record changes made
