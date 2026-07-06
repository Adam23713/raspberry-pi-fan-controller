from pathlib import Path


class CpuTemperatureReader:
    def __init__(self, temperature_file: str):
        self._temperature_file = Path(temperature_file)

    def read(self) -> float:
        return int(self._temperature_file.read_text().strip()) / 1000.0
