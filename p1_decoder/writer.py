"""Buffered NDJSON writer with rotation and compression."""

import json
import zstandard as zstd
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any
import anyio
import aiofiles

from p1_decoder.config import OUTPUT_DIR, FLUSH_LINES, FLUSH_MINUTES

EUROPE_AMSTERDAM = ZoneInfo("Europe/Amsterdam")
UTC = ZoneInfo("UTC")


class BufferedNDJSONWriter:
    """Buffered writer for NDJSON files with automatic flushing and rotation."""

    def __init__(self, suffix: str, output_dir: Path = OUTPUT_DIR):
        """
        Initialize buffered writer.

        Args:
            suffix: Suffix for file naming (e.g., 'electricity', 'gas', 'raw')
            output_dir: Directory to write files to
        """
        self.suffix = suffix
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.buffer: list[str] = []
        self.line_count = 0
        self.last_flush_time: datetime | None = None
        self.current_file: aiofiles.threadpool.AsyncTextIOWrapper | None = None
        self.current_file_path: Path | None = None
        self.current_hour: int | None = None
        self._shutdown = False

    async def _get_current_hour(self) -> int:
        """Get current hour in Europe/Amsterdam timezone."""
        now = datetime.now(EUROPE_AMSTERDAM)
        return now.hour

    async def _should_rotate(self) -> bool:
        """Check if file should be rotated (new hour)."""
        if self.current_hour is None:
            return False  # First file, don't rotate yet

        current_hour = await self._get_current_hour()
        return self.current_hour != current_hour

    def _get_filename(self, timestamp: datetime) -> Path:
        """Generate filename based on timestamp."""
        # Format: dsmr_2026-02-07T15-00-00+01:00_electricity.ndjson
        # Use hour boundary (minutes/seconds set to 0)
        hour_boundary = timestamp.replace(minute=0, second=0, microsecond=0)
        iso_str = hour_boundary.isoformat()
        # Replace colons in time portion but keep timezone offset format
        # 2026-02-07T15:00:00+01:00 -> 2026-02-07T15-00-00+01:00
        parts = iso_str.split("+")
        if len(parts) == 2:
            time_part = parts[0].replace(
                ":", "-", 2
            )  # Replace first 2 colons (in time)
            iso_str = f"{time_part}+{parts[1]}"
        else:
            # No timezone offset, just replace colons
            iso_str = iso_str.replace(":", "-", 2)
        return self.output_dir / f"dsmr_{iso_str}_{self.suffix}.ndjson"

    async def _open_file(self) -> None:
        """Open a new file for writing."""
        # Close existing file if open
        if self.current_file is not None:
            await self._close_file()

        now = datetime.now(EUROPE_AMSTERDAM)
        self.current_hour = now.hour
        self.current_file_path = self._get_filename(now)

        # Open file in append mode (text mode)
        self.current_file = await aiofiles.open(
            self.current_file_path, mode="a", encoding="utf-8"
        )

    async def _close_file(self) -> None:
        """Close current file and compress it."""
        if self.current_file is None:
            return

        await self.current_file.close()
        self.current_file = None

        # Compress the file asynchronously
        if self.current_file_path and self.current_file_path.exists():
            await self._compress_file(self.current_file_path)

        self.current_file_path = None

    async def _compress_file(self, file_path: Path) -> None:
        """Compress a file using zstd."""
        compressed_path = file_path.with_suffix(file_path.suffix + ".zst")

        # Read file content
        async with aiofiles.open(file_path, mode="rb") as f:
            content = await f.read()

        # Compress (run in thread to avoid blocking)
        def compress_data(data: bytes) -> bytes:
            cctx = zstd.ZstdCompressor()
            return cctx.compress(data)

        compressed = await anyio.to_thread.run_sync(compress_data, content)

        # Write compressed file
        async with aiofiles.open(compressed_path, mode="wb") as f:
            await f.write(compressed)

        # Remove original file
        file_path.unlink()

    async def _flush(self) -> None:
        """Flush buffer to file."""
        if not self.buffer:
            return

        if self.current_file is None:
            await self._open_file()

        # Write all buffered lines
        content = "\n".join(self.buffer) + "\n"
        await self.current_file.write(content)
        await self.current_file.flush()

        # Clear buffer
        self.buffer.clear()
        self.line_count = 0
        self.last_flush_time = datetime.now(EUROPE_AMSTERDAM)

    async def write(self, data: dict[str, Any]) -> None:
        """
        Write a JSON object to the buffer.

        Args:
            data: Dictionary to write as JSON line
        """
        if self._shutdown:
            return

        # Check if rotation is needed
        if await self._should_rotate():
            await self._flush()
            await self._close_file()
            await self._open_file()

        # Add to buffer
        json_line = json.dumps(data, ensure_ascii=False)
        self.buffer.append(json_line)
        self.line_count += 1

        # Check if flush is needed
        should_flush = False

        # Flush based on line count
        if self.line_count >= FLUSH_LINES:
            should_flush = True

        # Flush based on time
        if self.last_flush_time is not None:
            now = datetime.now(EUROPE_AMSTERDAM)
            elapsed = (now - self.last_flush_time).total_seconds() / 60
            if elapsed >= FLUSH_MINUTES:
                should_flush = True
        else:
            # First write, set flush time
            self.last_flush_time = datetime.now(EUROPE_AMSTERDAM)

        if should_flush:
            await self._flush()

    async def shutdown(self) -> None:
        """Shutdown writer: flush all buffers and close files."""
        self._shutdown = True
        await self._flush()
        await self._close_file()
