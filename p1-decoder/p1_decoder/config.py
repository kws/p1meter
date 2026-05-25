"""Configuration management using decouple."""

from pathlib import Path
from zoneinfo import ZoneInfo
from decouple import config

# MQTT Configuration
MQTT_BROKER_HOST = config("MQTT_BROKER_HOST", default="localhost")
MQTT_BROKER_PORT = config("MQTT_BROKER_PORT", cast=int, default=1883)
MQTT_TOPIC = config("MQTT_TOPIC", default="dsmr/raw/telegram")
MQTT_USERNAME = config("MQTT_USERNAME", default=None)
MQTT_PASSWORD = config("MQTT_PASSWORD", default=None)

# Output Configuration
OUTPUT_DIR = config("OUTPUT_DIR", cast=Path, default=Path("./cap"))

# Writer Configuration
FLUSH_LINES = config("FLUSH_LINES", cast=int, default=100)
FLUSH_MINUTES = config("FLUSH_MINUTES", cast=int, default=1)

# Timezone Configuration
UTC = ZoneInfo("UTC")
EUROPE_AMSTERDAM = ZoneInfo("Europe/Amsterdam")