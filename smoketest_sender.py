#!/usr/bin/env python3
"""Smoke test sender: reads log lines and publishes to MQTT for testing receiver resilience."""

import argparse
import json
import logging
import sys
from pathlib import Path
import anyio
from aiomqtt import Client
from p1_decoder.config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TOPIC,
    MQTT_USERNAME,
    MQTT_PASSWORD,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def send_log_lines(log_file: Path, delay: float = 0.0):
    """Read log file and publish raw telegram strings to MQTT."""
    client_kwargs = {
        "hostname": MQTT_BROKER_HOST,
        "port": MQTT_BROKER_PORT,
    }

    if MQTT_USERNAME:
        client_kwargs["username"] = MQTT_USERNAME
    if MQTT_PASSWORD:
        client_kwargs["password"] = MQTT_PASSWORD

    if not log_file.exists():
        logger.error(f"Log file not found: {log_file}")
        sys.exit(1)

    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    logger.info(f"Publishing to topic: {MQTT_TOPIC}")
    logger.info(f"Reading from log file: {log_file}")
    if delay > 0:
        logger.info(f"Delay between messages: {delay}s")

    count = 0
    async with Client(**client_kwargs) as client:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Parse NDJSON line
                        data = json.loads(line)
                        raw_telegram = data.get("raw")

                        if not raw_telegram:
                            logger.warning(
                                f"Line {line_num}: No 'raw' field found, skipping"
                            )
                            continue

                        # Publish to MQTT
                        await client.publish(MQTT_TOPIC, raw_telegram.encode("utf-8"))
                        count += 1

                        if count % 100 == 0:
                            logger.info(f"Published {count} messages...")

                        # Add delay if specified
                        if delay > 0:
                            await anyio.sleep(delay)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Line {line_num}: Invalid JSON, skipping: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Line {line_num}: Error processing line: {e}")
                        continue

            logger.info(f"Finished publishing {count} messages from {log_file}")

        except KeyboardInterrupt:
            logger.info(f"Interrupted. Published {count} messages before stopping.")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Read log lines and publish to MQTT for testing receiver resilience"
    )
    parser.add_argument(
        "log_file", type=Path, help="Path to NDJSON log file to read from"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds between messages (default: 0.0, no delay)",
    )

    args = parser.parse_args()
    await send_log_lines(args.log_file, args.delay)


if __name__ == "__main__":
    anyio.run(main)
