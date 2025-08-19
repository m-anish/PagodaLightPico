# Free MQTT Brokers for PagodaLightPico Project

This document recommends free-tier MQTT brokers that you can use with your PagodaLightPico system for receiving notifications about lighting changes and system events.

## Recommended Free MQTT Brokers

### 1. **HiveMQ Public Broker** (Default in config)
- **Host**: `broker.hivemq.com`
- **Port**: `1883` (unencrypted) or `8883` (TLS)
- **Features**: 
  - Free public broker
  - No registration required
  - Good for testing and development
  - No message persistence
- **Limitations**: Messages are not guaranteed delivery, no authentication
- **Best for**: Development, testing, non-critical notifications

### 2. **Eclipse IoT Mosquitto Public Broker**
- **Host**: `test.mosquitto.org`
- **Port**: `1883` (unencrypted) or `8883` (TLS)
- **Features**:
  - Free public broker
  - No registration required
  - Well-maintained by Eclipse Foundation
- **Limitations**: Public access, no message persistence
- **Best for**: Development and testing

### 3. **EMQX Cloud (Free Tier)** ⭐ RECOMMENDED
- **Host**: Your assigned endpoint (e.g., `c-xxx.emqx.cloud`)
- **Port**: `1883` or `8883`
- **Features**:
  - Free tier: 25 connections, 1M messages/month
  - Dashboard and monitoring
  - Authentication and access control
  - Message persistence
  - TLS encryption
- **Setup**: Register at https://cloud.emqx.com
- **Best for**: Production use with moderate traffic

### 4. **AWS IoT Core (Free Tier)**
- **Host**: Your AWS IoT endpoint
- **Port**: `8883` (TLS required)
- **Features**:
  - Free tier: 250,000 messages/month
  - Fully managed service
  - Integration with other AWS services
  - Certificate-based authentication
- **Limitations**: Requires AWS account and certificate setup
- **Best for**: Production use, AWS ecosystem integration

### 5. **Adafruit IO (Free Tier)**
- **Host**: `io.adafruit.com`
- **Port**: `1883` or `8883`
- **Features**:
  - Free tier: 30 data points/minute, 30 days retention
  - Easy web dashboard
  - RESTful API
  - Good documentation
- **Setup**: Register at https://io.adafruit.com
- **Best for**: Small projects with visualization needs

## Configuration Instructions

### For EMQX Cloud (Recommended)

1. **Sign up** at https://cloud.emqx.com
2. **Create a deployment** (select the free tier)
3. **Configure authentication**:
   - Go to Authentication & ACL → Authentication
   - Add a username/password for your device
4. **Get connection details**:
   - Note your broker endpoint (e.g., `c-xxx.emqx.cloud`)
   - Port: 1883 (unencrypted) or 8883 (TLS)

5. **Update your config.json**:
```json
{
  "notifications": {
    "enabled": true,
    "mqtt_broker": "c-your-cluster.emqx.cloud",
    "mqtt_port": 1883,
    "mqtt_topic": "PagodaLightPico/notifications",
    "mqtt_client_id": "PagodaLightPico",
    "notify_on_window_change": true,
    "notify_on_errors": true
  }
}
```

### For Public Brokers (HiveMQ/Mosquitto)

Simply update your config.json:
```json
{
  "notifications": {
    "enabled": true,
    "mqtt_broker": "broker.hivemq.com",
    "mqtt_port": 1883,
    "mqtt_topic": "PagodaLightPico/notifications",
    "mqtt_client_id": "PagodaLightPico_unique_id",
    "notify_on_window_change": true,
    "notify_on_errors": true
  }
}
```

**Important**: Use a unique client ID and topic to avoid conflicts with other users!

## Setting Up Notifications

Once your MQTT broker is configured, you can receive notifications through:

### 1. **Pushover** (Mobile push notifications)
- Use a service like Node-RED or Home Assistant to bridge MQTT → Pushover
- Subscribe to `PagodaLightPico/notifications/+` topic

### 2. **Home Assistant**
- Add MQTT integration
- Create automations based on received messages
- Send to mobile app or other notification services

### 3. **MQTT Client Apps**
- **MQTT Explorer** (Desktop)
- **MyMQTT** (Android)
- **MQTTool** (iOS)

### 4. **Custom Script**
Example Python script to monitor notifications:
```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        print(f"📱 {data['message']}")
    except:
        print(f"Raw message: {message.payload.decode()}")

client = mqtt.Client()
client.on_message = on_message
client.connect("broker.hivemq.com", 1883, 60)
client.subscribe("PagodaLightPico/notifications/+")
client.loop_forever()
```

## Topic Structure

Your PagodaLightPico device publishes to these topics:

- `PagodaLightPico/notifications/window_change` - Time window changes
- `PagodaLightPico/notifications/error` - System errors
- `PagodaLightPico/notifications/system` - Startup/shutdown events
- `PagodaLightPico/notifications/config` - Configuration updates

Each message contains JSON data with event details, timestamps, and device information.

## Security Considerations

- **Public brokers**: Anyone can potentially see your messages
- **Free tier services**: Limited features and message rates
- **Production use**: Consider paid tiers for better security and reliability
- **TLS encryption**: Use port 8883 when available for encrypted communication

## Troubleshooting

1. **Connection issues**: Check firewall settings, try different ports
2. **No messages**: Verify topic subscription and client ID uniqueness
3. **Authentication errors**: Double-check username/password in EMQX Cloud
4. **Rate limiting**: Monitor your message frequency on free tiers
