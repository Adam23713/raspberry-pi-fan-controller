from abc import ABC, abstractmethod
from pathlib import Path


class CpuTemperatureReader(ABC):
    @abstractmethod
    def read(self) -> float:
        """Return the current CPU temperature in degrees Celsius."""


class FileCpuTemperatureReader(CpuTemperatureReader):
    def __init__(self, temperature_file: str):
        self._temperature_file = Path(temperature_file)

    def read(self) -> float:
        return int(self._temperature_file.read_text().strip()) / 1000.0
