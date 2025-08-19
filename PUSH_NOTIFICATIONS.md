# Push Notification Setup Guide

This guide explains how to set up push notifications for your PagodaLight system using MQTT.

## Overview

The PagodaLight system can send push notifications to your mobile device when:
- Time windows change (e.g., switching from day to evening lighting)
- System errors occur
- Configuration is updated via web interface
- System starts up or shuts down

## Notification Flow

```
PagodaLight (Pico W) → MQTT Broker → Notification Service → Your Phone
```

## Setup Options

### Option 1: MQTT + Pushover (Recommended)

**Pushover** is a simple, reliable push notification service.

#### Step 1: Set up Pushover
1. Download Pushover app (iOS/Android) - $5 one-time fee
2. Create account at https://pushover.net/
3. Note your User Key from the dashboard

#### Step 2: Create Pushover Application
1. Go to https://pushover.net/apps/build
2. Create new application named "PagodaLight"
3. Note your API Token

#### Step 3: Set up MQTT-to-Pushover bridge
You can use Node-RED, Home Assistant, or a simple Python script:

**Python Bridge Script:**
```python
import paho.mqtt.client as mqtt
import requests
import json

PUSHOVER_TOKEN = "your_api_token"
PUSHOVER_USER = "your_user_key"

def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        
        # Send to Pushover
        requests.post("https://api.pushover.net/1/messages.json", data={
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "title": "🏯 PagodaLight",
            "message": data["message"],
            "priority": 1 if data.get("event") == "error" else 0
        })
        
    except Exception as e:
        print(f"Error: {e}")

client = mqtt.Client()
client.on_message = on_message
client.connect("broker.hivemq.com", 1883)
client.subscribe("pagoda_light/notifications/+")
client.loop_forever()
```

#### Step 4: Configure PagodaLight
Update `config.json`:
```json
{
  "notifications": {
    "enabled": true,
    "mqtt_broker": "broker.hivemq.com",
    "mqtt_port": 1883,
    "mqtt_topic": "pagoda_light/notifications",
    "mqtt_client_id": "pagoda_light_pico",
    "notify_on_window_change": true,
    "notify_on_errors": true
  }
}
```

### Option 2: MQTT + Home Assistant

If you use Home Assistant:

#### Step 1: Add MQTT Integration
1. In Home Assistant: Settings → Devices & Services → Add Integration
2. Search for "MQTT" and configure your broker

#### Step 2: Create Automation
```yaml
automation:
  - alias: "PagodaLight Notifications"
    trigger:
      - platform: mqtt
        topic: "pagoda_light/notifications/+/+"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🏯 PagodaLight"
          message: "{{ trigger.payload_json.message }}"
```

### Option 3: MQTT + Telegram Bot

#### Step 1: Create Telegram Bot
1. Message @BotFather on Telegram
2. Create new bot: `/newbot`
3. Note Bot Token and your Chat ID

#### Step 2: Python Bridge Script
```python
import paho.mqtt.client as mqtt
import requests
import json

BOT_TOKEN = "your_bot_token"
CHAT_ID = "your_chat_id"

def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        
        # Send to Telegram
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                     json={
                         "chat_id": CHAT_ID,
                         "text": data["message"]
                     })
    except Exception as e:
        print(f"Error: {e}")

client = mqtt.Client()
client.on_message = on_message
client.connect("broker.hivemq.com", 1883)
client.subscribe("pagoda_light/notifications/+")
client.loop_forever()
```

## MQTT Broker Options

### Public Brokers (Easy Setup)
- `broker.hivemq.com` (default)
- `test.mosquitto.org`
- `broker.emqx.io`

### Self-Hosted (More Secure)
- Install Mosquitto MQTT broker
- Use with Home Assistant
- Cloud services like AWS IoT, Google Cloud IoT

## Message Format

All notifications are published as JSON:

```json
{
  "event": "window_change",
  "window": "window_1",
  "duty_cycle": 60,
  "start_time": "18:00",
  "end_time": "20:00", 
  "message": "💡 Meditation lighting - 60% brightness",
  "timestamp": 1692419400,
  "device": "pagoda_light_pico"
}
```

## Topics

- `pagoda_light/notifications/window_change` - Time window changes
- `pagoda_light/notifications/error` - System errors  
- `pagoda_light/notifications/system` - Startup/shutdown
- `pagoda_light/notifications/config` - Configuration updates

## Troubleshooting

### No Notifications Received
1. Check `config.json` - ensure `enabled: true`
2. Check MQTT broker connectivity
3. Verify topic subscription in bridge script
4. Check PagodaLight logs for MQTT connection status

### Partial Notifications
1. Check notification preferences in config
2. Verify bridge script handles all topics
3. Check push service rate limits

### Test Notifications
You can test by publishing manually:
```bash
mosquitto_pub -h broker.hivemq.com -t "pagoda_light/notifications/test" -m '{"message":"Test notification"}'
```

## Security Considerations

1. **Use Authentication**: Configure MQTT broker with username/password
2. **Use TLS**: Enable SSL/TLS for MQTT connections  
3. **Private Broker**: Host your own MQTT broker for better security
4. **Topic Permissions**: Restrict topic access in broker configuration

## Advanced Features

### Conditional Notifications
Modify bridge script to filter notifications:
```python
# Only send notifications during specific hours
import datetime
hour = datetime.datetime.now().hour
if 6 <= hour <= 23:  # Only between 6 AM and 11 PM
    send_notification(data["message"])
```

### Custom Message Formatting
Customize notification text in bridge script:
```python
if data["event"] == "window_change":
    message = f"Lighting changed to {data['duty_cycle']}% brightness"
elif data["event"] == "error":
    message = f"⚠️ System error: {data['message']}"
```

### Multiple Recipients
Send to multiple devices/services:
```python
# Send to both Pushover and Telegram
send_pushover(message)
send_telegram(message)
send_email(message)  # Add email notifications
```
