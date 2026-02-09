from datetime import datetime, timedelta, timezone
from pathlib import Path
from decouple import config
import json
import csv
import re
from p1_decoder._pipeline import parse_timestamp
from p1_decoder.headers import code_lookup
from tqdm import tqdm

DATA_PATH = config("DATA_PATH", cast=Path)

CSV_HEADERS = [
    "telegram_timestamp",
    "electricity_import_t1_kwh",
    "electricity_import_t2_kwh",
    "electricity_export_t1_kwh",
    "electricity_export_t2_kwh",
    "active_tariff",
    "power_import_kw",
    "power_export_kw",
    "voltage_l1_v",
    "voltage_l2_v",
    "voltage_l3_v",
    "current_l1_a",
    "current_l2_a",
    "current_l3_a",
    "power_import_l1_kw",
    "power_import_l2_kw",
    "power_import_l3_kw",
    "power_export_l1_kw",
    "power_export_l2_kw",
    "power_export_l3_kw",
    "gas_reading_m3",
]


def read_data(path: Path = DATA_PATH):
    files = sorted(path.glob("*.ndjson"))
    for file in files:
        with open(file, "r") as f:
            for line in f:
                data = json.loads(line)
                yield data.get("raw")


def telegram_to_dict(telegram: str) -> dict:
    ptn = re.compile(r"^\d-\d:")
    lines = telegram.split("\n")
    data = {}
    for line in lines:
        if line and ptn.match(line):
            value_pos = line.find("(")
            key, value = line[:value_pos].strip(), line[value_pos:].strip()
            if value.count("(") == 1 and value.count(")") == 1:
                value = value[1:-1]
            data[key] = value
    return data


def extract_values(value: str):
    """Telegram packets are values surrounded by brackets ().
    Each line may contain multiple values, e.g. (v1)(v2)(v3).

    This function extracts all values from the string and returns them as a list.
    """
    values = []
    while "(" in value:
        start = value.find("(")
        end = value.find(")")
        values.append(value[start + 1 : end])
        value = value[end + 1 :]
    return values


def to_csv(path: Path = DATA_PATH):
    codes = code_lookup()
    header_lookup = {code.header: code for code in codes.values()}
    csv_path = path.with_suffix(".csv")
    with open(csv_path, "w") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        progress = tqdm(read_data(path), desc="Processing data")
        for data in progress:
            data = telegram_to_dict(data)
            progress.set_description(data.get("0-0:1.0.0"))
            row = []
            for header in CSV_HEADERS:
                code = header_lookup.get(header)
                if code:
                    row.append(data.get(code.dsmr))
                else:
                    row.append(None)
            writer.writerow(row)



def gas_csv(path: Path = DATA_PATH):
    gas_path = path.with_suffix(".gas.csv")
    with open(gas_path, "w") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "telegram_timestamp",
                "gas_reading_m3",
                "gas_usage_m3",
                "gas_usage_m3_per_hour",
            ]
        )
        last_reading = last_reading_m3 = last_timestamp = None
        progress = tqdm(read_data(path), desc="Processing data")
        for data in progress:
            data = telegram_to_dict(data)
            reading = data.get("0-1:24.2.1")
            if reading == last_reading:
                continue
            timestamp_str, reading_m3 = extract_values(reading)
            timestamp = parse_timestamp(timestamp_str)

            reading_m3 = float(reading_m3.replace("*m3", ""))

            usage_m3 = reading_m3 - last_reading_m3 if last_reading_m3 else "-"
            delta = timestamp - last_timestamp if last_timestamp else None
            if delta is None or delta < timedelta(seconds=1):
                usage_m3_per_hour = "-"
            else:
                usage_m3_per_hour = usage_m3 / (delta.total_seconds() / 3600)
                usage_m3_per_hour = round(usage_m3_per_hour, 2)

            if usage_m3 != "-":
                usage_m3 = f"{usage_m3:0.4f}"

            writer.writerow(
                [
                    f"{timestamp:%Y%m%d%H%M%S}",
                    f"{reading_m3:4.2f}",
                    usage_m3,
                    usage_m3_per_hour,
                ]
            )
            last_reading = reading
            last_reading_m3 = reading_m3
            last_timestamp = timestamp


if __name__ == "__main__":
    to_csv(DATA_PATH)
    gas_csv(DATA_PATH)
