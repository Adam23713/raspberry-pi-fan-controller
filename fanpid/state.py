from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Optional


@dataclass(frozen=True)
class FanStatus:
    raw_temperature: Optional[float] = None
    temperature: Optional[float] = None
    duty: float = 0.0
    updated_at: Optional[float] = None


class FanState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._status = FanStatus()

    def update(
        self,
        raw_temperature: float,
        temperature: float,
        duty: float,
    ) -> None:
        status = FanStatus(
            raw_temperature=raw_temperature,
            temperature=temperature,
            duty=duty,
            updated_at=time(),
        )
        with self._lock:
            self._status = status

    def snapshot(self) -> FanStatus:
        with self._lock:
            return self._status
