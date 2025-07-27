"""Configuration module for B2500 Load Distributor."""

import os
from typing import Optional


def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with optional default."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} is required but not set")
    return value


def get_env_int(key: str, default: Optional[int] = None) -> int:
    """Get environment variable as integer with optional default."""
    value = os.getenv(key)
    if value is None:
        if default is None:
            raise ValueError(f"Environment variable {key} is required but not set")
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {key} must be an integer, got: {value}")


def get_env_float(key: str, default: Optional[float] = None) -> float:
    """Get environment variable as float with optional default."""
    value = os.getenv(key)
    if value is None:
        if default is None:
            raise ValueError(f"Environment variable {key} is required but not set")
        return default
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Environment variable {key} must be a float, got: {value}")


class Config:
    """Configuration class for B2500 Load Distributor."""
    
    # MQTT Configuration
    MQTT_BROKER = get_env_var("MQTT_BROKER")
    MQTT_PORT = get_env_int("MQTT_PORT", 1883)
    MQTT_USERNAME = get_env_var("MQTT_USERNAME")
    MQTT_PASSWORD = get_env_var("MQTT_PASSWORD")
    
    # MQTT Topics
    SOURCE_TOPIC = get_env_var("SOURCE_TOPIC", "sma")
    OUTPUT_TOPIC = get_env_var("OUTPUT_TOPIC", "sma/net_power")
    STORAGE1_OUTPUT_TOPIC = get_env_var("STORAGE1_OUTPUT_TOPIC", "sma/net_power/1")
    STORAGE2_OUTPUT_TOPIC = get_env_var("STORAGE2_OUTPUT_TOPIC", "sma/net_power/2")
    STORAGE1_BATTERY_TOPIC = get_env_var("STORAGE1_BATTERY_TOPIC", "b2500/1/battery/remaining_percent")
    STORAGE2_BATTERY_TOPIC = get_env_var("STORAGE2_BATTERY_TOPIC", "b2500/2/battery/remaining_percent")
    STORAGE1_POWER_TOPIC = get_env_var("STORAGE1_POWER_TOPIC", "b2500/1/power/power")
    STORAGE2_POWER_TOPIC = get_env_var("STORAGE2_POWER_TOPIC", "b2500/2/power/power")
    STORAGE1_CONNECTED_TOPIC = get_env_var("STORAGE1_CONNECTED_TOPIC", "b2500/1/smartmeter/connected")
    STORAGE2_CONNECTED_TOPIC = get_env_var("STORAGE2_CONNECTED_TOPIC", "b2500/2/smartmeter/connected")
    
    # Power Limits (Watts)
    MIN_POWER = get_env_int("MIN_POWER", 40)
    MAX_POWER = get_env_int("MAX_POWER", 400)
    MAX_POWER_BOOST = get_env_int("MAX_POWER_BOOST", 100)
    
    # Control Parameters
    DEFAULT_BATTERY_PERCENT = get_env_float("DEFAULT_BATTERY_PERCENT", 80.0)
    DEFAULT_POWER_OUTPUT = get_env_float("DEFAULT_POWER_OUTPUT", 200.0)
    REBALANCE_THRESHOLD = get_env_int("REBALANCE_THRESHOLD", 3)
    REBALANCE_RATE = get_env_float("REBALANCE_RATE", 1.0)
    MIN_PUBLISH_CHANGE = get_env_int("MIN_PUBLISH_CHANGE", 0)
    
    # Logging Configuration
    LOG_LEVEL = get_env_var("LOG_LEVEL", "INFO")