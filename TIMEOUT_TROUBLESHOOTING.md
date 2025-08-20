# ETIMEDOUT Error Troubleshooting Guide

If you're experiencing random "Error 500 [Errno 110] ETIMEDOUT" errors, this guide will help you diagnose and resolve the issue.

## What is ETIMEDOUT?

ETIMEDOUT (Error 110) occurs when network operations take too long to complete. This can happen with:
- Web server requests
- MQTT connections
- WiFi connectivity issues
- Memory pressure causing delays

## Quick Fixes

### 1. Check Your WiFi Signal
- Ensure your Pico W is within good range of your WiFi router
- Check for interference from other devices
- Consider moving closer to the router or using a WiFi extender

### 2. Adjust Timeout Settings
Edit your `config.json` file to include network timeout settings:

```json
{
  "network": {
    "web_server_timeout": 5,
    "mqtt_keepalive": 60,
    "mqtt_timeout": 15,
    "wifi_reconnect_interval": 30,
    "memory_warning_threshold": 8000
  }
}
```

**Settings explained:**
- `web_server_timeout`: Seconds to wait for web requests (default: 3)
- `mqtt_keepalive`: MQTT keepalive interval in seconds (default: 30)
- `mqtt_timeout`: MQTT connection timeout in seconds (default: 10)
- `wifi_reconnect_interval`: How often to check WiFi health (default: 30)
- `memory_warning_threshold`: Memory threshold for warnings in bytes (default: 10000)

### 3. Monitor System Health
Monitor your logs periodically for signs of instability, such as:
- WiFi disconnections/reconnect attempts
- MQTT disconnects or publish failures
- Web server request timeouts
- Low-memory warnings and current free memory

Look for patterns in these messages to identify problem areas.

## Advanced Troubleshooting

### Memory Issues
If you see frequent "Low memory warning" messages:
1. Increase `memory_warning_threshold` to 15000 or higher
2. Restart the system periodically
3. Disable MQTT notifications if not needed
4. Consider reducing `update_interval` in system settings

### WiFi Stability Issues
If WiFi keeps disconnecting:
1. Check router settings for power saving modes
2. Ensure your router supports the Pico W's WiFi standards
3. Try a different WiFi channel on your router
4. Increase `wifi_reconnect_interval` to reduce checking frequency

### MQTT Connection Issues
If MQTT keeps disconnecting:
1. Verify your MQTT broker is stable and accessible
2. Increase `mqtt_keepalive` to 60 or 120 seconds
3. Increase `mqtt_timeout` to 20 seconds
4. Consider using a local MQTT broker instead of cloud-based

### Web Server Timeouts
If web interface is slow or timing out:
1. Increase `web_server_timeout` to 5 or 10 seconds
2. Access the web interface from the same network as the Pico W
3. Avoid accessing multiple pages simultaneously
4. Clear your browser cache

## Monitoring Commands

To check system health, look for these kinds of log messages:
- `Low memory warning` - Indicates memory pressure
- `Request timeout (ETIMEDOUT)` - Web server timeout events
- `MQTT ... (ETIMEDOUT)` - MQTT publish/connect timeout events

## Configuration Examples

### For Stable Networks (Low Latency)
```json
"network": {
  "web_server_timeout": 2,
  "mqtt_keepalive": 30,
  "mqtt_timeout": 8,
  "wifi_reconnect_interval": 60
}
```

### For Unstable Networks (High Latency)
```json
"network": {
  "web_server_timeout": 10,
  "mqtt_keepalive": 120,
  "mqtt_timeout": 30,
  "wifi_reconnect_interval": 15
}
```

### For Memory-Constrained Setups
```json
"network": {
  "memory_warning_threshold": 5000
},
"notifications": {
  "enabled": false
}
```

## When to Restart

Consider restarting the system if you see:
- Memory warnings every few minutes
- More than 10 timeout errors per hour
- WiFi disconnections more than once per hour
- Web interface becomes unresponsive

## Getting Help

If timeouts persist after trying these solutions:
1. Check the diagnostic logs for patterns
2. Note your network environment (router model, distance, interference)
3. Document the frequency and timing of errors
4. Consider your specific use case and adjust settings accordingly

The system is designed to automatically recover from most timeout issues, but proper configuration for your environment will minimize their occurrence.