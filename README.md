# B2500 Load Distributor

A smart MQTT-based power distribution controller that manages two B2500 battery storage systems by dynamically distributing power loads based on battery levels, system availability, and consumption patterns.

## Overview

This system monitors your home's net power consumption via MQTT and intelligently distributes the power load between two B2500 battery storage systems. It automatically adjusts the power distribution based on:

- Battery charge levels (prioritizes discharging higher-charged batteries)
- System availability (handles offline/online states)
- Power limits and constraints
- Real-time power consumption data

## Features

- **Intelligent Load Balancing**: Automatically distributes power based on battery levels
- **Fault Tolerance**: Continues operation when one storage system is offline
- **Real-time Monitoring**: Live battery percentage and power output tracking
- **MQTT Integration**: Seamless integration with existing home automation systems
- **Docker Support**: Easy deployment with Docker Compose
- **Configurable Parameters**: Adjustable power limits, rebalancing thresholds, and more

## Prerequisites

### Required Components

1. **b2500-meter**: You need the [b2500-meter](https://github.com/tomquist/b2500-meter) project running for each B2500 storage system
2. **esphome-b2500**: You need [esphome-b2500](https://github.com/tomquist/esphome-b2500) for battery levels and power information from each B2500 system
3. **MQTT Broker**: A running MQTT broker (like Mosquitto)
4. **Smart Meter Data**: SMA smart meter data published to MQTT
5. **Docker**: For containerized deployment

### B2500-Meter Setup

Each B2500 storage system requires:
1. **esphome-b2500** running on an ESP32 device connected to the B2500 for battery and power data
2. **b2500-meter** instance to receive power control commands

See the example b2500-meter configurations in this repository:

#### Storage 1 Configuration (`examples/b2500-meter-config/storage-1/config.ini`):
```ini
[GENERAL]
DEVICE_TYPE = shellyemg3
SKIP_POWERMETER_TEST = False
THROTTLE_INTERVAL = 5

[MQTT]
BROKER = your_mqtt_broker_ip
PORT = 1883
TOPIC = sma/net_power/1
USERNAME = your_mqtt_username
PASSWORD = your_mqtt_password
```

#### Storage 2 Configuration (`examples/b2500-meter-config/storage-2/config.ini`):
```ini
[GENERAL]
DEVICE_TYPE = shellyproem50
SKIP_POWERMETER_TEST = False
THROTTLE_INTERVAL = 5

[MQTT]
BROKER = your_mqtt_broker_ip
PORT = 1883
TOPIC = sma/net_power/2
USERNAME = your_mqtt_username
PASSWORD = your_mqtt_password
```

**Important**: Each b2500-meter must publish to a unique MQTT topic (`sma/net_power/1` and `sma/net_power/2`).

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# MQTT Configuration
MQTT_BROKER=your_mqtt_broker_ip
MQTT_PORT=1883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password

# MQTT Topics
SOURCE_TOPIC=sma
OUTPUT_TOPIC=sma/net_power
STORAGE1_OUTPUT_TOPIC=sma/net_power/1
STORAGE2_OUTPUT_TOPIC=sma/net_power/2
STORAGE1_BATTERY_TOPIC=b2500/1/battery/remaining_percent
STORAGE2_BATTERY_TOPIC=b2500/2/battery/remaining_percent
STORAGE1_POWER_TOPIC=b2500/1/power/power
STORAGE2_POWER_TOPIC=b2500/2/power/power
STORAGE1_CONNECTED_TOPIC=b2500/1/smartmeter/connected
STORAGE2_CONNECTED_TOPIC=b2500/2/smartmeter/connected

# Power Limits (Watts)
MIN_POWER=40
MAX_POWER=400
MAX_POWER_BOOST=100

# Control Parameters
DEFAULT_BATTERY_PERCENT=80.0
DEFAULT_POWER_OUTPUT=200.0
REBALANCE_THRESHOLD=3
REBALANCE_RATE=1.0
MIN_PUBLISH_CHANGE=0
```

## Installation & Deployment

### Method 1: Docker Compose (Recommended)

1. Clone this repository
2. Copy `.env.example` to `.env` and configure your settings
3. Start the service:

```bash
docker-compose up -d
```

### Method 2: Manual Python Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables or edit the script directly
3. Run the script:
```bash
python mqtt_net_power_calculator.py
```

## MQTT Topics

### Input Topics (Subscribed)
- `sma` - Smart meter data (consumption/feed-in)
- `b2500/1/battery/remaining_percent` - Storage 1 battery level
- `b2500/2/battery/remaining_percent` - Storage 2 battery level  
- `b2500/1/power/power` - Storage 1 current power output
- `b2500/2/power/power` - Storage 2 current power output
- `b2500/1/smartmeter/connected` - Storage 1 connection status
- `b2500/2/smartmeter/connected` - Storage 2 connection status

### Output Topics (Published)
- `sma/net_power` - Calculated net power consumption
- `sma/net_power/1` - Power adjustment for Storage 1
- `sma/net_power/2` - Power adjustment for Storage 2

## How It Works

1. **Power Monitoring**: Continuously monitors net power consumption from smart meter data
2. **Battery Balancing**: Distributes load to maintain balanced battery levels between storage systems
3. **Availability Handling**: Automatically adjusts when storage systems go offline/online
4. **Power Limiting**: Respects minimum and maximum power constraints for each storage system
5. **Real-time Adjustment**: Publishes power adjustments to MQTT topics that b2500-meter instances consume

### Load Distribution Algorithm

- **Balanced Mode**: When battery levels are similar (within threshold), distributes load equally
- **Rebalancing Mode**: When battery levels differ significantly, prioritizes discharging the higher-charged battery
- **Offline Handling**: Redirects all load to the online storage system when one goes offline
- **Power Limits**: Ensures each storage system operates within safe power limits

## Monitoring

The system provides real-time console output showing:
- Current battery levels for both storage systems
- Power output changes
- System status (online/offline)
- Load distribution decisions

Example output:
```
2025-07-27 08:01:51,087 - __main__ - INFO - Net Power: 150W
2025-07-27 08:01:51,087 - __main__ - INFO - Storage 1 (ONLINE): 85.2% 200→250W (+50)
2025-07-27 08:01:51,087 - __main__ - INFO - Storage 2 (ONLINE): 78.9% 200→300W (+100)
2025-07-27 08:01:51,087 - __main__ - INFO - Total Output: 400→550W
```

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check MQTT broker settings and credentials
2. **No Data Received**: Ensure b2500-meter instances are running and publishing data
3. **Unbalanced Distribution**: Verify battery level topics are being received correctly
4. **Storage Offline**: Check network connectivity and b2500-meter configurations

### Debug Mode

Enable debug logging by setting the log level in the Python script or add verbose output flags.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Related Projects

- [b2500-meter](https://github.com/tomquist/b2500-meter) - Essential companion project for B2500 integration
- [esphome-b2500](https://github.com/tomquist/esphome-b2500) - Essential companion project for B2500 integration

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the b2500-meter documentation
3. Open an issue on GitHub with detailed logs and configuration