from contextlib import asynccontextmanager
from dataclasses import dataclass
from aiomqtt import Client
import logging

import anyio
from p1_decoder.config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TOPIC,
    MQTT_USERNAME,
    MQTT_PASSWORD,
)

logger = logging.getLogger(__name__)


def _get_connection_args():
    """Subscribe to MQTT and yield raw telegram strings."""
    client_kwargs = {
        "hostname": MQTT_BROKER_HOST,
        "port": MQTT_BROKER_PORT,
    }

    if MQTT_USERNAME:
        client_kwargs["username"] = MQTT_USERNAME
    if MQTT_PASSWORD:
        client_kwargs["password"] = MQTT_PASSWORD

    return client_kwargs

async def mqtt_subscriber():
    client_kwargs = _get_connection_args()
    async with Client(**client_kwargs) as client:
        await client.subscribe(MQTT_TOPIC)
        async for message in client.messages:
            if message.payload:
                payload = message.payload.decode("utf-8", errors="ignore")
                logger.debug(payload)
                yield payload


@dataclass(frozen=True, slots=True, kw_only=True)
class MQTTMessage:
    topic: str
    value: str


async def _publish_message(client: Client, receive_stream: anyio.abc.ObjectReceiveStream[MQTTMessage]):
    async for message in receive_stream:
        try:
            await client.publish(message.topic, message.value.encode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to publish message: {e}", exc_info=True)
            continue

@asynccontextmanager
async def mqtt_publisher():
    client_kwargs = _get_connection_args()
    async with Client(**client_kwargs) as client:
        send_stream, receive_stream = anyio.create_memory_object_stream(max_buffer_size=100, item_type=MQTTMessage)
        async with anyio.create_task_group() as tg:
            tg.start_soon(_publish_message, client, receive_stream)
            yield send_stream
            tg.cancel_scope.cancel()
            await send_stream.aclose()
            await receive_stream.aclose()


