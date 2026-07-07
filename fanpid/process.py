from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock

import psutil


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_bytes: int


class ProcessMonitorService(ABC):
    @abstractmethod
    def get_top_processes(self, limit: int = 5) -> list[ProcessInfo]:
        """Return the processes using the most CPU."""


class PsutilProcessMonitorService(ProcessMonitorService):
    def __init__(self) -> None:
        self._lock = Lock()
        self._prime_cpu_measurements()

    def get_top_processes(self, limit: int = 5) -> list[ProcessInfo]:
        processes = []
        with self._lock:
            for process in psutil.process_iter():
                try:
                    processes.append(
                        ProcessInfo(
                            pid=process.pid,
                            name=process.name(),
                            cpu_percent=process.cpu_percent(interval=None),
                            memory_percent=process.memory_percent(),
                            memory_bytes=process.memory_info().rss,
                        )
                    )
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue

        processes.sort(
            key=lambda process: (process.cpu_percent, process.memory_bytes),
            reverse=True,
        )
        return processes[:limit]

    def _prime_cpu_measurements(self) -> None:
        for process in psutil.process_iter():
            try:
                process.cpu_percent(interval=None)
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
