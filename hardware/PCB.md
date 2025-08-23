# Rev0 LED Driver Board (Pico-W + PT4115 + Peripherals) ⚡💡

This document describes the first revision (Rev0) of a 2-layer PCB incorporating a Raspberry Pi Pico-W, PT4115 LED drivers, an LM2596 buck regulator, a DS3231 RTC module, and support circuitry.

---

## Main Components 🧩

1. **Raspberry Pi Pico-W** 🐦
   - Mounted via 2.54mm pin headers.
   - Provides GPIO control and PWM dimming.

2. **PT4115 LED Drivers (x5)** 💡💡💡💡💡
   - Exposed via 2.54mm headers:  
     `In+`, `In+`, `In-`, `In-`, `PWM`, `LED+`, `LED-`.
   - PWM dimming controlled from Pico GPIOs.
   - Screw terminals provided for `LED+` and `LED-`.

3. **LM2596 Buck Module** 🔋
   - Solderable footprint for standard off-the-shelf module.
   - Steps down up to +30VDC input → +5V for Pico-W.

4. **DS3231 RTC Module** ⏰
   - 5-pin header: `3V3`, `SDA`, `SCL`, `NC`, `GND`.
   - Connected to Pico GPIO20 (SDA) and GPIO21 (SCL).

5. **RGB Status LED** 🌈
   - 0805 package, driven by Pico GPIO13, GPIO14, GPIO15.
   - Current-limiting resistors included.

---

## GPIO Mapping 🗺️

| Pico GPIO | Function                     |
|-----------|------------------------------|
| GP13      | RGB LED (Red) 🔴             |
| GP14      | RGB LED (Green) 🟢           |
| GP15      | RGB LED (Blue) 🔵            |
| GP16      | PWM for PT4115 Driver #1 💡  |
| GP17      | PWM for PT4115 Driver #2 💡  |
| GP18      | PWM for PT4115 Driver #3 💡  |
| GP19      | PWM for PT4115 Driver #4 💡  |
| GP22      | PWM for PT4115 Driver #5 💡  |
| GP20      | SDA (to DS3231) ↔️           |
| GP21      | SCL (to DS3231) ↔️           |

---

## Power Input & Protection 🔌🛡️

- Single screw terminal for **+30VDC input**.
- Reverse polarity protection diode at input.
- LM2596 regulates down to **+5V** for Pico and peripherals.

---

## RC Filters for PWM 🎚️

Each PT4115 driver PWM pin has optional RC filter pads:
- **Resistor**: 10k (0805) 🟦
- **Capacitor**: 1µF (0805) 🟨

---

## Mechanical Features ⚙️

- PCB outline: rectangle with 3mm radius rounded corners.
- Mounting holes: M3, located 6mm from each board corner 🔩.

---

