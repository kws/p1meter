from dataclasses import dataclass
from decimal import Decimal
import re
from datetime import datetime, timedelta, timezone
from typing import Callable

TELEGRAM_PTN = re.compile(r"^\d-\d:")
POWER_IMPORT_PHASE_FIELDS = (
    "power_import_l1_kw",
    "power_import_l2_kw",
    "power_import_l3_kw",
)
POWER_EXPORT_PHASE_FIELDS = (
    "power_export_l1_kw",
    "power_export_l2_kw",
    "power_export_l3_kw",
)
INSTANTANEOUS_POWER_FIELDS = frozenset(
    {
        "power_import_kw",
        "power_export_kw",
        *POWER_IMPORT_PHASE_FIELDS,
        *POWER_EXPORT_PHASE_FIELDS,
    }
)


def rounder(ndigits: int) -> Callable[[str], float]:
    if ndigits < 0:
        return float
    elif ndigits == 0:
        return lambda val: int(float(val))
    return lambda val: round(float(val), ndigits)


@dataclass(frozen=True, slots=True, kw_only=True)
class Value:
    value: str
    unit: str | None = None

    def __repr__(self) -> str:
        if self.unit:
            return f"{self.value} {self.unit}"
        else:
            return self.value

@dataclass(frozen=True, slots=True, kw_only=True)
class ElectricityReading:
    timestamp: int
    meter_id: str
    import_t1_kwh: Value
    import_t2_kwh: Value
    export_t1_kwh: Value
    export_t2_kwh: Value
    active_tariff: Value
    power_import_kw: Value
    power_export_kw: Value
    voltage_l1_v: Value
    voltage_l2_v: Value
    voltage_l3_v: Value
    current_l1_a: Value
    current_l2_a: Value
    current_l3_a: Value
    power_import_l1_kw: Value
    power_import_l2_kw: Value
    power_import_l3_kw: Value
    power_export_l1_kw: Value
    power_export_l2_kw: Value
    power_export_l3_kw: Value

    def _sum_fields(self, fields: tuple[str, ...]) -> Decimal:
        return sum((Decimal(getattr(self, field).value) for field in fields), Decimal("0"))

    def to_dict(self, round: int = -1) -> dict:
        tofloat = rounder(round)
        power_import_phase_sum_kw = self._sum_fields(POWER_IMPORT_PHASE_FIELDS)
        power_export_phase_sum_kw = self._sum_fields(POWER_EXPORT_PHASE_FIELDS)
        power_net_kw = power_import_phase_sum_kw - power_export_phase_sum_kw

        return {
            "timestamp": self.timestamp,
            "meter_id": self.meter_id,
            "import_t1_kwh": tofloat(self.import_t1_kwh.value),
            "import_t2_kwh": tofloat(self.import_t2_kwh.value),
            "export_t1_kwh": tofloat(self.export_t1_kwh.value),
            "export_t2_kwh": tofloat(self.export_t2_kwh.value),
            "active_tariff": int(self.active_tariff.value),
            "power_import_kw": tofloat(self.power_import_kw.value),
            "power_export_kw": tofloat(self.power_export_kw.value),
            "voltage_l1_v": tofloat(self.voltage_l1_v.value),
            "voltage_l2_v": tofloat(self.voltage_l2_v.value),
            "voltage_l3_v": tofloat(self.voltage_l3_v.value),
            "current_l1_a": tofloat(self.current_l1_a.value),
            "current_l2_a": tofloat(self.current_l2_a.value),
            "current_l3_a": tofloat(self.current_l3_a.value),
            "power_import_l1_kw": tofloat(self.power_import_l1_kw.value),
            "power_import_l2_kw": tofloat(self.power_import_l2_kw.value),
            "power_import_l3_kw": tofloat(self.power_import_l3_kw.value),
            "power_export_l1_kw": tofloat(self.power_export_l1_kw.value),
            "power_export_l2_kw": tofloat(self.power_export_l2_kw.value),
            "power_export_l3_kw": tofloat(self.power_export_l3_kw.value),
            "power_import_phase_sum_kw": tofloat(str(power_import_phase_sum_kw)),
            "power_export_phase_sum_kw": tofloat(str(power_export_phase_sum_kw)),
            "power_net_kw": tofloat(str(power_net_kw)),
        }

    def only_changes(self, last_reading: "ElectricityReading | None", tolerance: float = 0.1) -> "ElectricityReading | None":
        if last_reading is None:
            return self

        new_reading = {
            "timestamp": self.timestamp,
            "meter_id": self.meter_id,
        }
        changed = False

        for field in self.__dataclass_fields__:
            if field in ["timestamp", "meter_id"]:
                continue
            value_obj = getattr(self, field)
            value = float(value_obj.value)

            old_value_obj = getattr(last_reading, field)
            old_value = float(old_value_obj.value)

            zero_power_transition = (
                field in INSTANTANEOUS_POWER_FIELDS
                and value == 0
                and old_value != 0
            )

            if zero_power_transition or abs(value - old_value) > tolerance:
                new_reading[field] = value_obj
                changed = True
            else:
                new_reading[field] = old_value_obj

        if not changed:
            return None

        return ElectricityReading(**new_reading)


@dataclass(frozen=True, slots=True, kw_only=True)
class GasReading:
    timestamp: int
    meter_id: str
    reading_m3: Value

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "meter_id": self.meter_id,
            "reading_m3": float(self.reading_m3.value),
        }

def _parse_value(value: str) -> Value:
    if "*" in value:
        value, unit = value.split("*")
        return Value(value=value, unit=unit)
    else:
        return Value(value=value)


def parse_timestamp(timestamp: str | Value) -> datetime:
    """
    The time data is always in LOCAL TIME for Europe/Amsterdam.
    If the last character is a W it means we are in winter time,
    and if it is a S it means we are in summer time.

    The format is:
        YYMMDDHHMMSS[W|S]

    Example:
        260207163214W
        -> 2026-02-07 16:32:14 Europe/Amsterdam
        260517120000S
        -> 2026-05-17 12:00:00 Europe/Amsterdam

    To avoid timezone switch issues, we will use W to mean UTC+1, and S to mean UTC+2.

    Returns:
        A parsed datetime object in Europe/Amsterdam timezone.
    """
    if isinstance(timestamp, Value):
        timestamp = timestamp.value
    if len(timestamp) != 13:
        raise ValueError(
            "Timestamp must be 13 characters long. We got %s" % len(timestamp)
        )
    year = int(timestamp[:2]) + 2000
    month = int(timestamp[2:4])
    day = int(timestamp[4:6])
    hour = int(timestamp[6:8])
    minute = int(timestamp[8:10])
    second = int(timestamp[10:12])
    timezone_str = timestamp[12:14]

    if timezone_str == "W":
        timezone_value = timezone(timedelta(hours=1))
    elif timezone_str == "S":
        timezone_value = timezone(timedelta(hours=2))
    else:
        raise ValueError("Invalid timezone")
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone_value)


def telegram_to_dict(telegram: str) -> dict:
    lines = telegram.split("\n")
    data = {}
    for line in lines:
        if line and TELEGRAM_PTN.match(line):
            value_pos = line.find("(")
            key, value = line[:value_pos].strip(), line[value_pos:].strip()
            value_list = value.split("(")
            value_list = [value[:-1] for value in value_list if value.strip()]
            value_list = [_parse_value(value) for value in value_list]
            if len(value_list) == 1:
                data[key] = value_list[0]
            else:
                data[key] = tuple(value_list)
    return data


def split_telegram_dict(telegram_dict: dict) -> tuple[dict, dict]:
    electricity_dict = {}
    gas_dict = {}
    for key, value in telegram_dict.items():
        if key.startswith("1-0:"):
            electricity_dict[key] = value
        elif key.startswith("0-1:"):
            gas_dict[key] = value
    return electricity_dict, gas_dict


def to_readings(telegram_dict: dict) -> tuple[ElectricityReading, GasReading]:
    electricity_reading = ElectricityReading(
        timestamp=int(parse_timestamp(telegram_dict["0-0:1.0.0"]).timestamp()),
        meter_id=telegram_dict["0-0:96.1.1"],
        import_t1_kwh=telegram_dict["1-0:1.8.1"],
        import_t2_kwh=telegram_dict["1-0:1.8.2"],
        export_t1_kwh=telegram_dict["1-0:2.8.1"],
        export_t2_kwh=telegram_dict["1-0:2.8.2"],
        active_tariff=telegram_dict["0-0:96.14.0"],
        power_import_kw=telegram_dict["1-0:1.7.0"],
        power_export_kw=telegram_dict["1-0:2.7.0"],
        voltage_l1_v=telegram_dict["1-0:32.7.0"],
        voltage_l2_v=telegram_dict["1-0:52.7.0"],
        voltage_l3_v=telegram_dict["1-0:72.7.0"],
        current_l1_a=telegram_dict["1-0:31.7.0"],
        current_l2_a=telegram_dict["1-0:51.7.0"],
        current_l3_a=telegram_dict["1-0:71.7.0"],
        power_import_l1_kw=telegram_dict["1-0:21.7.0"],
        power_import_l2_kw=telegram_dict["1-0:41.7.0"],
        power_import_l3_kw=telegram_dict["1-0:61.7.0"],
        power_export_l1_kw=telegram_dict["1-0:22.7.0"],
        power_export_l2_kw=telegram_dict["1-0:42.7.0"],
        power_export_l3_kw=telegram_dict["1-0:62.7.0"],
    )
    
    timestamp_str, reading_m3 = telegram_dict["0-1:24.2.1"]
    timestamp = int(parse_timestamp(timestamp_str).timestamp())

    gas_reading = GasReading(
        timestamp=timestamp,
        meter_id=telegram_dict["0-0:96.1.1"],
        reading_m3=reading_m3,
    )

    return electricity_reading, gas_reading
