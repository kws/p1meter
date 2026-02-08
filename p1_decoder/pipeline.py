"""Async pipeline components for P1 telegram processing."""

from zoneinfo import ZoneInfo
from p1_decoder.reader import parse_timestamp, extract_values

EUROPE_AMSTERDAM = ZoneInfo("Europe/Amsterdam")


def parse_timestamp_to_epoch(timestamp_str: str) -> int:
    """
    Parse P1 timestamp and convert to Unix epoch seconds.

    Args:
        timestamp_str: P1 timestamp in format YYMMDDHHMMSS[W|S]

    Returns:
        Unix epoch seconds (UTC)
    """
    dt = parse_timestamp(timestamp_str)
    # Convert to UTC for epoch calculation
    return int(dt.timestamp())


def parse_telegram_timestamp(telegram_dict: dict) -> int | None:
    """
    Extract and parse telegram timestamp (0-0:1.0.0) to Unix epoch seconds.

    Args:
        telegram_dict: Parsed telegram dictionary

    Returns:
        Unix epoch seconds or None if timestamp not found
    """
    timestamp_str = telegram_dict.get("0-0:1.0.0")
    if not timestamp_str:
        return None
    return parse_timestamp_to_epoch(timestamp_str)


def parse_gas_timestamp(gas_reading: str) -> int | None:
    """
    Extract and parse gas reading timestamp from 0-1:24.2.1 to Unix epoch seconds.

    Args:
        gas_reading: Raw gas reading value from OBIS code 0-1:24.2.1

    Returns:
        Unix epoch seconds or None if parsing fails
    """
    if not gas_reading:
        return None
    try:
        values = extract_values(gas_reading)
        if len(values) >= 1:
            timestamp_str = values[0]
            return parse_timestamp_to_epoch(timestamp_str)
    except (ValueError, IndexError):
        pass
    return None


def extract_gas_reading_m3(gas_reading: str) -> float | None:
    """
    Extract gas reading value in m3 from 0-1:24.2.1.

    Args:
        gas_reading: Raw gas reading value from OBIS code 0-1:24.2.1

    Returns:
        Gas reading value in m3 or None if parsing fails
    """
    if not gas_reading:
        return None
    try:
        values = extract_values(gas_reading)
        if len(values) >= 2:
            reading_str = values[1].replace("*m3", "").replace("*m³", "")
            return float(reading_str)
    except (ValueError, IndexError):
        pass
    return None


def electricity_filter(telegram_dict: dict) -> dict:
    """
    Filter out gas-only OBIS codes (codes starting with 0-1:).

    Args:
        telegram_dict: Parsed telegram dictionary

    Returns:
        Filtered dictionary with only electricity-related codes
    """
    filtered = {}
    for key, value in telegram_dict.items():
        if not key.startswith("0-1:"):
            filtered[key] = value
    return filtered


def gas_filter(
    telegram_dict: dict, last_gas_reading: str | None
) -> tuple[dict | None, str | None]:
    """
    Filter for gas data and deduplicate.

    Args:
        telegram_dict: Parsed telegram dictionary
        last_gas_reading: Last seen gas reading value (raw string)

    Returns:
        Tuple of (gas_dict if changed, new_last_gas_reading)
        gas_dict will be None if reading hasn't changed
    """
    gas_reading = telegram_dict.get("0-1:24.2.1")

    # If no gas reading, return None
    if not gas_reading:
        return None, last_gas_reading

    # If reading hasn't changed, skip
    if gas_reading == last_gas_reading:
        return None, last_gas_reading

    # Extract gas-related codes
    gas_dict = {}
    for key, value in telegram_dict.items():
        if key.startswith("0-1:"):
            gas_dict[key] = value

    return gas_dict, gas_reading
