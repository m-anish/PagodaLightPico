# Installing mDNS Support for MicroPython

The mDNS (Multicast DNS) functionality requires additional modules that may not be included by default in your MicroPython installation.

## 🔍 Quick Check

If you see this error when running the code:
```
ImportError: no module named 'mdns'
```

Then you need to install mDNS support using one of the methods below.

## 📦 Installation Methods

### Method 1: Using mip (MicroPython Package Installer)

If you're using a recent version of MicroPython (1.19+):

```python
# On your Pico W, run:
import mip
mip.install("mdns")
```

### Method 2: Manual Installation

1. **Download the mdns module files** from the MicroPython library
2. **Copy to your device** in the `/lib` folder
3. **Restart your device**

### Method 3: Using mpremote (if available)

```bash
# From your computer:
mpremote mip install mdns
```

### Method 4: Check MicroPython Distribution

Some MicroPython builds for Pico W may include mDNS support by default. Try:

```python
# Test if mdns is available:
try:
    import mdns
    print("✅ mDNS module is available!")
except ImportError:
    print("❌ mDNS module not found")
```

## 🔧 Alternative Solutions

If you can't get mDNS working, you can still use the system effectively:

### Option 1: Use IP Address
Instead of `http://lighthouse.local/`, use the device's IP address:
- Check your router's admin panel for connected devices
- Use network scanner apps like Fing or LanScan
- The device logs will show the IP address on startup

### Option 2: Static IP Configuration
Configure your router to assign a static IP to your Pico W based on its MAC address.

### Option 3: Router DNS
Some routers allow you to set custom local DNS entries.

## 📊 Checking Installation Status

The system gracefully handles missing mDNS support:

- ✅ **mDNS Available**: Device discoverable as `lighthouse.local`
- ⚠️ **mDNS Unavailable**: Device accessible only via IP address

You'll see this in the logs:
```
WARN: mDNS module not available - device will only be accessible via IP address
INFO: To enable mDNS discovery, install the mdns module for MicroPython
```

## 🛠️ Troubleshooting

### Issue: Module installs but doesn't work
- Restart the Pico W after installation
- Check that the module is in the correct `/lib` directory
- Verify your MicroPython version supports mDNS

### Issue: Network discovery still doesn't work
- Ensure your router supports multicast traffic
- Check that devices are on the same network segment
- Some enterprise/guest networks block mDNS

### Issue: Hostname conflicts
- If `lighthouse.local` is taken, the system may append numbers
- Customize the hostname in `lib/mdns_service.py`

## ✅ Verification

To verify mDNS is working:

1. **Run the test script**: `python test_mdns.py`
2. **Check the logs** for "mDNS service started" messages
3. **Try accessing** `http://lighthouse.local/` in a browser
4. **Use network discovery tools** to find the device

## 🆘 Need Help?

If you're still having issues:
1. Check the MicroPython version: `import sys; print(sys.implementation)`
2. List installed modules: `help('modules')`  
3. Check available memory: `import gc; print(gc.mem_free())`

The system works perfectly without mDNS - it just means you'll need to use IP addresses instead of friendly hostnames! 🏮
