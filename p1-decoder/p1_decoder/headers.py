from pathlib import Path
from typing import Generator
from decouple import config
import yaml
from dataclasses import dataclass

DEFAULT_CODES_PATH = Path(__file__).parent / "headers.yml"
CODES_PATH = config("CODES_PATH", cast=Path, default=DEFAULT_CODES_PATH)


@dataclass(frozen=True, slots=True, kw_only=True)
class Code:
    dsmr: str
    header: str
    name: str
    unit: str


def read_codes(path: Path = CODES_PATH) -> Generator[Code, None, None]:
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    codes = data.get("dsmr_p1", {})
    for code, value in codes.items():
        yield Code(
            dsmr=code,
            header=value.get("header"),
            name=value.get("name"),
            unit=value.get("unit"),
        )


def code_lookup(path: Path = CODES_PATH) -> dict[str, Code]:
    codes = read_codes(path)
    return {code.dsmr: code for code in codes}


class HeaderTool:
    def __init__(self, path: Path = CODES_PATH):
        self.codes = code_lookup(path)
        self.headers = {code.header: code for code in self.codes.values()}

    def get_from_dsmr(self, dsmr: str) -> Code:
        return self.codes.get(dsmr)

    def get_from_header(self, header: str) -> Code:
        return self.headers.get(header)

    def rename_keys(self, telegram_dict: dict) -> dict:
        output_dict = {}
        for dsmr, value in telegram_dict.items():
            code = self.get_from_dsmr(dsmr)
            if code:
                output_dict[code.header] = value
            else:
                output_dict[dsmr] = value
        return output_dict