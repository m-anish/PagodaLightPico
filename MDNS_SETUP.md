# mDNS Device Discovery Setup

Your PagodaLight device now supports mDNS (Multicast DNS) for easy discovery on your local network! This means you can access your device using a friendly hostname instead of remembering IP addresses.

> **⚠️ Note**: mDNS requires additional modules that may not be included by default. If you see "ImportError: no module named 'mdns'", please see [INSTALL_MDNS.md](INSTALL_MDNS.md) for installation instructions. The system works perfectly without mDNS - you'll just need to use IP addresses instead of friendly hostnames.

## 🎯 Quick Access

Once your device is connected to WiFi, you can access it at:
- **http://lighthouse.local/** (default hostname)
- Or the traditional IP address method: http://[device-ip]/

## 🔧 Customizing the Hostname

You can easily customize the device name by editing `lib/mdns_service.py`. Look for this line at the bottom of the file:

```python
mdns_service = MDNSService(hostname="lighthouse", service_name="PagodaLight Meditation Center")
```

### Cute Hostname Ideas:
- `"lighthouse"` → **lighthouse.local** (default)
- `"pagoda"` → **pagoda.local**
- `"zen"` → **zen.local**  
- `"sanctuary"` → **sanctuary.local**
- `"temple"` → **temple.local**
- `"lotus"` → **lotus.local**
- `"meditation"` → **meditation.local**
- `"peace"` → **peace.local**
- `"serenity"` → **serenity.local**
- `"enlighten"` → **enlighten.local**

## 🌐 What Gets Advertised

The mDNS service advertises:

1. **HTTP Service** (`_http._tcp`)
   - Your web configuration interface
   - Includes device information and feature flags

2. **Custom Pagoda Service** (`_pagoda._tcp`)
   - For potential future integration with specialized apps
   - Identifies the device type as meditation lighting

## 🔍 Discovery Methods

### macOS/iOS:
- Safari: Just type `lighthouse.local` in the address bar
- Finder: Look under "Network" in the sidebar
- iOS: Works in Safari and other apps that support Bonjour

### Windows:
- Install Bonjour Print Services from Apple
- Or use any browser that supports mDNS resolution

### Linux:
- Most modern distributions support mDNS out of the box
- Install `avahi-daemon` if needed: `sudo apt install avahi-daemon`

### Network Discovery Tools:
- **LanScan** (iOS/macOS): Shows all network devices
- **Fing** (iOS/Android): Network scanner with device details
- **Discovery DNS-SD Browser**: See all mDNS services on your network

## 📊 Status Monitoring

The web interface now shows mDNS status in the system status section. You'll see:
- ✅ **mDNS ✓** when the service is running properly  
- ❌ **mDNS ✗** when there's an issue with the service

## 🛠️ Troubleshooting

### Device Not Found:
1. Ensure WiFi is connected (mDNS requires network connectivity)
2. Check that your router supports multicast (most modern routers do)
3. Try accessing via IP address first to verify the web server is running
4. Restart the device to reinitialize mDNS service

### Hostname Conflicts:
If another device on your network has the same hostname, the device will automatically append a number (e.g., `lighthouse-2.local`)

### Network Segmentation:
mDNS typically works within the same network segment. If you're on a different VLAN or subnet, you may not be able to discover the device.

## 🧪 Testing mDNS Functionality

A standalone test script is provided to verify mDNS functionality independently:

```bash
# On your Pico W, run:
python test_mdns.py
```

The test script will:
1. **Connect to WiFi** using settings from `config.json`
2. **Show network diagnostics** (IP address, signal strength, etc.)
3. **Start a test mDNS service** as `test-lighthouse.local`
4. **Run for 30 seconds** to allow discovery testing
5. **Update service info** midway through the test
6. **Clean up and report results**

### Expected Output:
```
INFO: 🚀 Starting comprehensive mDNS test...
INFO: 🌐 Step 1: Connecting to WiFi...
INFO: ✅ WiFi connected successfully with IP: 192.168.1.100
INFO: 📊 Step 2: Network diagnostics...
INFO:    IP Address: 192.168.1.100
INFO: 🏮 Step 3: Testing mDNS service...
INFO: ✅ mDNS service started successfully
INFO: 🔗 Test URL: http://test-lighthouse.local/
INFO: 🎉 mDNS test PASSED
```

## 🔄 Making Changes

After changing the hostname in `mdns_service.py`:
1. Save the file
2. Restart your PagodaLight device
3. The new hostname will be available within 30-60 seconds
4. Check the system logs for confirmation: "mDNS service started - device discoverable as 'yourhostname.local'"

Enjoy your friendlier device discovery! 🏮✨
