from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import anyio
from p1_decoder._anyio import setup_scope_signal_handlers
from p1_decoder._mqtt import mqtt_subscriber
import aiofiles

from p1_decoder.writer import EUROPE_AMSTERDAM, UTC
import logging

logger = logging.getLogger(__name__)

FLUSH_PERIOD = timedelta(minutes=1)
FLUSH_LINES = 50


async def mqtt_loop(send_stream: anyio.abc.ObjectSendStream[str]):
    try:
        async for raw_telegram in mqtt_subscriber():
            try:
                await send_stream.send(raw_telegram)
            except Exception as e:
                logger.error(f"Failed to send message to stream: {e}", exc_info=True)
                # Continue processing next message
    except Exception as e:
        logger.error(f"MQTT subscriber error: {e}", exc_info=True)
        raise  # Re-raise to allow task group to handle


async def test_loop(send_stream: anyio.abc.ObjectSendStream[str]):
    counter = 0
    while True:
        await send_stream.send(f"Test {counter}")
        counter += 1
        if counter > 67:
            raise ValueError("Test loop cancelled")
        await anyio.sleep(0.1)


class ArchiveWriter:
    def __init__(self, archive_path: Path):
        self.archive_path = archive_path
        self._total_lines_written = 0
        self._current_file = None
        self._lines_written = 0
        self._last_flush_time = datetime.now(EUROPE_AMSTERDAM)

    async def write_loop(self, receive_stream: anyio.abc.ObjectReceiveStream[str]):
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._flush_loop)
            tg.start_soon(self._rollover_loop)

            try:
                async for message in receive_stream:
                    await self._write_to_archive(message)

            finally:
                tg.cancel_scope.cancel()
                with anyio.CancelScope(shield=True):
                    with anyio.fail_after(2):
                        await self._close()

    async def _close(self):
        if self._current_file is not None:
            current_file, self._current_file = self._current_file, None
            await current_file.close()
            logger.info(f"Closed file {current_file.name}")

    async def _flush(self):
        if self._current_file is None:
            return
        self._lines_written = 0
        self._last_flush_time = datetime.now(EUROPE_AMSTERDAM)
        await self._current_file.flush()
        logger.info(
            f"Flushed file {self._current_file.name} after writing {self._total_lines_written} lines"
        )

    async def _write_to_archive(self, message: str):
        # Input validation (nice to have)
        if message is None:
            logger.warning("Received None message, skipping")
            return
        if not isinstance(message, str):
            logger.warning(
                f"Received non-string message (type: {type(message).__name__}), skipping"
            )
            return
        if not message:
            logger.warning("Received empty message, skipping")
            return

        timestamp = datetime.now(EUROPE_AMSTERDAM)

        # Open file if needed
        if self._current_file is None:
            try:
                date_str = timestamp.strftime("%Y%m%d")
                timestamps_str = timestamp.strftime("%Y%m%d%H%M%S%z")
                archive_path = self.archive_path / f"{date_str}"
                try:
                    archive_path.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError) as e:
                    logger.error(
                        f"Failed to create archive directory {archive_path}: {e}",
                        exc_info=True,
                    )
                    return

                try:
                    file_path = archive_path / f"{timestamps_str}.ndjson"
                    self._current_file = await aiofiles.open(
                        file_path, mode="w", encoding="utf-8"
                    )
                    logger.info(f"Opened new archive file: {file_path}")
                except (OSError, PermissionError) as e:
                    logger.error(
                        f"Failed to open archive file {file_path}: {e}", exc_info=True
                    )
                    return
            except Exception as e:
                logger.error(
                    f"Unexpected error opening archive file: {e}", exc_info=True
                )
                return

        # Write message to file
        try:
            self._total_lines_written += 1
            try:
                json_line = json.dumps(
                    {
                        "ts_utc": timestamp.astimezone(UTC).isoformat(),
                        "seq": self._total_lines_written,
                        "raw": message,
                        "raw_bytes": len(message),
                    }
                )
            except (TypeError, ValueError) as e:
                logger.error(
                    f"Failed to serialize message to JSON (seq: {self._total_lines_written}, message length: {len(message)}): {e}",
                    exc_info=True,
                )
                return

            await self._current_file.write(json_line)
            await self._current_file.write("\n")
            self._lines_written += 1

            if self._lines_written >= FLUSH_LINES:
                await self._flush()
        except (OSError, PermissionError) as e:
            logger.error(
                f"Failed to write to archive file (seq: {self._total_lines_written}): {e}",
                exc_info=True,
            )
            # Continue processing next message
        except Exception as e:
            logger.error(
                f"Unexpected error writing to archive (seq: {self._total_lines_written}): {e}",
                exc_info=True,
            )
            # Continue processing next message

    async def _flush_loop(self):
        while True:
            try:
                now = datetime.now(EUROPE_AMSTERDAM)
                if self._current_file is not None:
                    if now - self._last_flush_time > FLUSH_PERIOD:
                        try:
                            await self._flush()
                        except Exception as e:
                            logger.error(
                                f"Error flushing file in flush loop: {e}", exc_info=True
                            )
                            # Continue loop despite flush failure

                time_to_next_flush = (self._last_flush_time + FLUSH_PERIOD) - now
                sleep_seconds = max(0.0, time_to_next_flush.total_seconds())
                await anyio.sleep(sleep_seconds)
            except Exception as e:
                logger.error(f"Unexpected error in flush loop: {e}", exc_info=True)
                # Continue loop to prevent complete failure
                await anyio.sleep(FLUSH_PERIOD.total_seconds())

    async def _rollover_loop(self):
        while True:
            try:
                if self._current_file is not None:
                    day_of_last_flush = self._last_flush_time.date()
                    day_of_now = datetime.now(EUROPE_AMSTERDAM).date()

                    if day_of_last_flush != day_of_now:
                        try:
                            current_file, self._current_file = self._current_file, None
                            self._last_flush_time = datetime.now(EUROPE_AMSTERDAM)
                            self._lines_written = 0
                            await current_file.close()
                            logger.info(
                                f"Rolled over to new day, closed file: {current_file.name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error closing file during rollover: {e}",
                                exc_info=True,
                            )
                            # Continue loop despite close failure

                await anyio.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error in rollover loop: {e}", exc_info=True)
                # Continue loop to prevent complete failure
                await anyio.sleep(1)


async def main():
    send_stream, receive_stream = anyio.create_memory_object_stream(max_buffer_size=100)

    archive_writer = ArchiveWriter(Path("./archive"))

    async with anyio.create_task_group() as tg:
        setup_scope_signal_handlers(tg.cancel_scope)
        tg.start_soon(mqtt_loop, send_stream)
        # tg.start_soon(test_loop, send_stream)
        tg.start_soon(archive_writer.write_loop, receive_stream)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    anyio.run(main)
