from aiomqtt import Client
import logging
from p1_decoder.config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TOPIC,
    MQTT_USERNAME,
    MQTT_PASSWORD,
)

logger = logging.getLogger(__name__)

async def mqtt_subscriber():
    """Subscribe to MQTT and yield raw telegram strings."""
    client_kwargs = {
        "hostname": MQTT_BROKER_HOST,
        "port": MQTT_BROKER_PORT,
    }
    
    if MQTT_USERNAME:
        client_kwargs["username"] = MQTT_USERNAME
    if MQTT_PASSWORD:
        client_kwargs["password"] = MQTT_PASSWORD
    
    async with Client(**client_kwargs) as client:
        await client.subscribe(MQTT_TOPIC)
        async for message in client.messages:
            if message.payload:
                payload = message.payload.decode('utf-8', errors='ignore')
                logger.debug(payload)
                yield payload