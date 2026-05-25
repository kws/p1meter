"""Main entry point for P1 MQTT pipeline."""

import logging
import sys
import anyio
from p1_decoder._anyio import setup_signal_handlers
from p1_decoder._mqtt import mqtt_subscriber
from p1_decoder.pipeline import (
    telegram_to_dict,
    parse_telegram_timestamp,
    parse_gas_timestamp,
    extract_gas_reading_m3,
    electricity_filter,
    gas_filter,
)
from p1_decoder.writer import BufferedNDJSONWriter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def process_electricity(
    telegram_dict: dict,
    timestamp_epoch: int | None,
    writer: BufferedNDJSONWriter,
) -> None:
    """Process and write electricity data."""
    try:
        filtered = electricity_filter(telegram_dict)

        # Add timestamp as epoch
        output = {"timestamp": timestamp_epoch}

        # Add all electricity fields
        for key, value in filtered.items():
            output[key] = value

        await writer.write(output)
    except Exception as e:
        logger.error(f"Error processing electricity data: {e}", exc_info=True)


async def process_gas(
    telegram_dict: dict,
    writer: BufferedNDJSONWriter,
    last_gas_reading: list[str | None],  # Use list to allow mutation in async
) -> None:
    """Process and write gas data (only when changed)."""
    try:
        gas_dict, new_last_reading = gas_filter(telegram_dict, last_gas_reading[0])

        if gas_dict is None:
            return

        # Update last reading
        last_gas_reading[0] = new_last_reading

        # Extract gas reading and timestamp
        gas_reading_raw = gas_dict.get("0-1:24.2.1", "")
        timestamp_epoch = parse_gas_timestamp(gas_reading_raw)
        gas_reading_m3 = extract_gas_reading_m3(gas_reading_raw)

        # Build output
        output = {"timestamp": timestamp_epoch}

        # Add gas reading value
        if gas_reading_m3 is not None:
            output["gas_reading_m3"] = gas_reading_m3

        # Add all gas fields
        for key, value in gas_dict.items():
            output[key] = value

        await writer.write(output)
    except Exception as e:
        logger.error(f"Error processing gas data: {e}", exc_info=True)


async def process_raw(
    raw_telegram: str,
    writer: BufferedNDJSONWriter,
) -> None:
    """Process and write raw telegram."""
    try:
        output = {"raw": raw_telegram}
        await writer.write(output)
    except Exception as e:
        logger.error(f"Error processing raw data: {e}", exc_info=True)


async def main_loop():
    """Main processing loop."""
    # Create writers
    electricity_writer = BufferedNDJSONWriter("electricity")
    gas_writer = BufferedNDJSONWriter("gas")
    raw_writer = BufferedNDJSONWriter("raw")

    # State for gas deduplication
    last_gas_reading: list[str | None] = [None]

    try:
        async for raw_telegram in mqtt_subscriber():
            try:
                # Parse telegram
                telegram_dict = telegram_to_dict(raw_telegram)

                # Extract timestamp
                timestamp_epoch = parse_telegram_timestamp(telegram_dict)

                # Process in parallel
                async with anyio.create_task_group() as tg:
                    # Electricity
                    tg.start_soon(
                        process_electricity,
                        telegram_dict,
                        timestamp_epoch,
                        electricity_writer,
                    )

                    # Gas (with deduplication)
                    tg.start_soon(
                        process_gas,
                        telegram_dict,
                        gas_writer,
                        last_gas_reading,
                    )

                    # Raw
                    tg.start_soon(
                        process_raw,
                        raw_telegram,
                        raw_writer,
                    )
            except Exception as e:
                logger.error(f"Error processing telegram: {e}", exc_info=True)
                # Continue processing next telegram

    except KeyboardInterrupt:
        logger.info("Received shutdown signal, flushing buffers...")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
    finally:
        # Shutdown: flush all buffers
        await electricity_writer.shutdown()
        await gas_writer.shutdown()
        await raw_writer.shutdown()


async def main():
    """Main entry point."""
    setup_signal_handlers()
    await main_loop()


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        sys.exit(0)
