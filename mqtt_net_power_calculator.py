#!/usr/bin/env python3
"""B2500 Load Distributor - Smart MQTT-based power distribution controller.

This module manages two B2500 battery storage systems by dynamically distributing
power loads based on battery levels, system availability, and consumption patterns.
"""

import paho.mqtt.client as mqtt
import json
import time
import signal
import sys
import logging
from datetime import datetime
from config import Config

# Configure logging
log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

running = True


class PowerController:
    """Manages power distribution between two B2500 storage systems."""
    def __init__(self):
        """Initialize the PowerController with default storage states."""
        self.storage_state = {
            '1': {
                'battery_percent': Config.DEFAULT_BATTERY_PERCENT,
                'current_power': Config.DEFAULT_POWER_OUTPUT,
                'is_online': True,
                'has_battery_data': False,
                'has_power_data': False
            },
            '2': {
                'battery_percent': Config.DEFAULT_BATTERY_PERCENT,
                'current_power': Config.DEFAULT_POWER_OUTPUT,
                'is_online': True,
                'has_battery_data': False,
                'has_power_data': False
            }
        }
        self.last_published = {'1': None, '2': None}
        logger.info(f"Initialized: Both storages at {Config.DEFAULT_BATTERY_PERCENT}%, {Config.DEFAULT_POWER_OUTPUT}W")

    def update_connection_status(self, storage_id: str, connected: bool) -> None:
        """Update the connection status of a storage system.
        
        Args:
            storage_id: The storage system ID ('1' or '2')
            connected: Whether the storage system is connected
        """
        storage = self.storage_state[storage_id]
        old_status = storage['is_online']
        storage['is_online'] = connected
        if old_status != connected:
            logger.info(f"Storage {storage_id}: {'ONLINE' if connected else 'OFFLINE'}")

    def calculate_power_distribution(self, net_power: float) -> tuple[float | None, float | None]:
        """Calculate optimal power distribution between storage systems.
        
        Args:
            net_power: The net power consumption/generation
            
        Returns:
            Tuple of (net_power1, net_power2) or (None, None) if both systems offline
        """
        s1 = self.storage_state['1'].copy()
        s2 = self.storage_state['2'].copy()
        s1_online = s1['is_online']
        s2_online = s2['is_online']

        if not s1_online and not s2_online:
            logger.warning("Both storage systems offline!")
            return None, None
        if not s1_online:
            logger.info("Storage 1 offline - redirecting all power to Storage 2")
            return 0, net_power
        if not s2_online:
            logger.info("Storage 2 offline - redirecting all power to Storage 1")
            return net_power, 0

        storage1_battery = s1['battery_percent']
        storage2_battery = s2['battery_percent']
        storage1_power = s1['current_power']
        storage2_power = s2['current_power']

        using_defaults = []
        if not s1['has_battery_data']: using_defaults.append("S1bat")
        if not s1['has_power_data']: using_defaults.append("S1pwr")
        if not s2['has_battery_data']: using_defaults.append("S2bat")
        if not s2['has_power_data']: using_defaults.append("S2pwr")
        if using_defaults:
            logger.debug(f"Using default values for: {', '.join(using_defaults)}")

        total_current_output = storage1_power + storage2_power
        desired_total_output = total_current_output + net_power

        if desired_total_output >= 2 * Config.MAX_POWER:
            target1 = target2 = Config.MAX_POWER + Config.MAX_POWER_BOOST
            net_power1 = target1 - storage1_power
            net_power2 = target2 - storage2_power
            logger.info("Operating in MAX POWER MODE")
            return net_power1, net_power2
        elif desired_total_output <= 2 * Config.MIN_POWER:
            net_power1 = Config.MIN_POWER - storage1_power
            net_power2 = Config.MIN_POWER - storage2_power
            logger.info("Operating in MIN POWER MODE")
            return net_power1, net_power2

        battery_diff = storage1_battery - storage2_battery

        if abs(battery_diff) < Config.REBALANCE_THRESHOLD:
            weight1 = weight2 = 0.5
        else:
            total_battery = storage1_battery + storage2_battery
            if total_battery == 0:
                base_weight1 = base_weight2 = 0.5
            else:
                base_weight1 = storage1_battery / total_battery
                base_weight2 = storage2_battery / total_battery

            if battery_diff > 0:
                rebalance_shift = Config.REBALANCE_RATE * (battery_diff / 100)
                weight1 = base_weight1 + rebalance_shift
                weight2 = base_weight2 - rebalance_shift
            else:
                rebalance_shift = Config.REBALANCE_RATE * (-battery_diff / 100)
                weight1 = base_weight1 - rebalance_shift
                weight2 = base_weight2 + rebalance_shift

            weight1 = max(0.1, min(0.9, weight1))
            weight2 = max(0.1, min(0.9, weight2))
            total_weight = weight1 + weight2
            weight1 /= total_weight
            weight2 /= total_weight

        target_output1 = desired_total_output * weight1
        target_output2 = desired_total_output * weight2

        if target_output1 < Config.MIN_POWER:
            target_output1 = Config.MIN_POWER
            target_output2 = desired_total_output - target_output1
        elif target_output1 > Config.MAX_POWER:
            target_output1 = Config.MAX_POWER
            target_output2 = desired_total_output - target_output1

        if target_output2 < Config.MIN_POWER:
            target_output2 = Config.MIN_POWER
            target_output1 = desired_total_output - target_output2
        elif target_output2 > Config.MAX_POWER:
            target_output2 = Config.MAX_POWER
            target_output1 = desired_total_output - target_output2

        net_power1 = target_output1 - storage1_power
        net_power2 = target_output2 - storage2_power
        return net_power1, net_power2

    def should_publish(self, storage_id: str, new_value: float) -> bool:
        """Determine if a new value should be published based on change threshold.
        
        Args:
            storage_id: The storage system ID ('1' or '2')
            new_value: The new power value to potentially publish
            
        Returns:
            True if the value should be published, False otherwise
        """
        if self.last_published[storage_id] is None:
            return True
        return abs(new_value - self.last_published[storage_id]) >= Config.MIN_PUBLISH_CHANGE

    def publish_updates(self, client: mqtt.Client, net_power: float, net_power1: float, net_power2: float) -> None:
        """Publish power updates to MQTT topics.
        
        Args:
            client: The MQTT client instance
            net_power: The net power consumption
            net_power1: Power adjustment for storage 1
            net_power2: Power adjustment for storage 2
        """
        s1 = self.storage_state['1']
        s2 = self.storage_state['2']
        net_power1_rounded = round(net_power1)
        net_power2_rounded = round(net_power2)
        new_power1 = round(s1['current_power'] + net_power1)
        new_power2 = round(s2['current_power'] + net_power2)

        publish1 = self.should_publish('1', net_power1_rounded)
        publish2 = self.should_publish('2', net_power2_rounded)

        if publish1:
            result = client.publish(Config.STORAGE1_OUTPUT_TOPIC, str(net_power1_rounded), retain=True)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish to Storage 1: {mqtt.error_string(result.rc)}")
            else:
                self.last_published['1'] = net_power1_rounded

        if publish2:
            result = client.publish(Config.STORAGE2_OUTPUT_TOPIC, str(net_power2_rounded), retain=True)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish to Storage 2: {mqtt.error_string(result.rc)}")
            else:
                self.last_published['2'] = net_power2_rounded

        if publish1 or publish2:
            status1 = "ONLINE" if s1['is_online'] else "OFFLINE"
            status2 = "ONLINE" if s2['is_online'] else "OFFLINE"
            logger.info(f"Net Power: {round(net_power)}W")
            logger.info(f"Storage 1 ({status1}): {s1['battery_percent']:.1f}% {round(s1['current_power'])}→{new_power1}W ({net_power1_rounded:+d})")
            logger.info(f"Storage 2 ({status2}): {s2['battery_percent']:.1f}% {round(s2['current_power'])}→{new_power2}W ({net_power2_rounded:+d})")
            logger.info(f"Total Output: {round(s1['current_power'] + s2['current_power'])}→{new_power1 + new_power2}W")

controller = PowerController()


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Received shutdown signal, stopping gracefully...")
    running = False

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback for when the MQTT client connects to the broker."""
    if rc == 0:
        logger.info(f"Connected to MQTT broker {Config.MQTT_BROKER}:{Config.MQTT_PORT}")
        topics = [
            Config.SOURCE_TOPIC,
            Config.STORAGE1_BATTERY_TOPIC,
            Config.STORAGE2_BATTERY_TOPIC,
            Config.STORAGE1_POWER_TOPIC,
            Config.STORAGE2_POWER_TOPIC,
            Config.STORAGE1_CONNECTED_TOPIC,
            Config.STORAGE2_CONNECTED_TOPIC
        ]
        for topic in topics:
            client.subscribe(topic)
    else:
        logger.error(f"MQTT connection failed with code: {rc}")

def on_message(client, userdata, msg):
    """Callback for when a message is received from the MQTT broker."""
    global controller
    topic = msg.topic

    try:
        if topic == Config.SOURCE_TOPIC:
            data = json.loads(msg.payload.decode())
            consumption = data['1-0:1.7.0']['value']
            feedin = data['1-0:2.7.0']['value']
            net_power = consumption - feedin

            result = client.publish(Config.OUTPUT_TOPIC, str(round(net_power)), retain=True)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish net power: {mqtt.error_string(result.rc)}")

            net_power1, net_power2 = controller.calculate_power_distribution(net_power)
            if net_power1 is not None and net_power2 is not None:
                controller.publish_updates(client, net_power, net_power1, net_power2)

        elif topic == Config.STORAGE1_BATTERY_TOPIC:
            old_value = controller.storage_state['1']['battery_percent']
            new_value = float(msg.payload.decode())
            controller.storage_state['1']['battery_percent'] = new_value
            controller.storage_state['1']['has_battery_data'] = True
            if old_value is not None and abs(new_value - old_value) > 1:
                logger.debug(f"Storage 1 battery: {old_value:.1f}→{new_value:.1f}%")

        elif topic == Config.STORAGE2_BATTERY_TOPIC:
            old_value = controller.storage_state['2']['battery_percent']
            new_value = float(msg.payload.decode())
            controller.storage_state['2']['battery_percent'] = new_value
            controller.storage_state['2']['has_battery_data'] = True
            if old_value is not None and abs(new_value - old_value) > 1:
                logger.debug(f"Storage 2 battery: {old_value:.1f}→{new_value:.1f}%")

        elif topic == Config.STORAGE1_POWER_TOPIC:
            power_value = float(msg.payload.decode())
            controller.storage_state['1']['current_power'] = power_value
            controller.storage_state['1']['has_power_data'] = True

        elif topic == Config.STORAGE2_POWER_TOPIC:
            power_value = float(msg.payload.decode())
            controller.storage_state['2']['current_power'] = power_value
            controller.storage_state['2']['has_power_data'] = True

        elif topic == Config.STORAGE1_CONNECTED_TOPIC:
            connected = msg.payload.decode().upper() == "ON"
            controller.update_connection_status('1', connected)

        elif topic == Config.STORAGE2_CONNECTED_TOPIC:
            connected = msg.payload.decode().upper() == "ON"
            controller.update_connection_status('2', connected)

    except Exception as e:
        logger.error(f"Error processing message from {topic}: {e}")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

try:
    logger.info("Starting B2500 Load Distribution Controller")
    logger.info(f"Power limits: {Config.MIN_POWER}-{Config.MAX_POWER}W, Rebalance threshold: {Config.REBALANCE_THRESHOLD}%")
    logger.info(f"Connecting to MQTT broker {Config.MQTT_BROKER}:{Config.MQTT_PORT}...")
    client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
    client.loop_start()
    while running:
        time.sleep(1)
except Exception as e:
    logger.error(f"Application error: {e}")
finally:
    logger.info("Cleaning up and shutting down...")
    client.loop_stop()
    client.disconnect()
