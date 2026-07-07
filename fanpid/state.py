from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Lock
from time import time
from typing import Optional


class ControlMode(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


@dataclass(frozen=True)
class FanStatus:
    raw_temperature: Optional[float] = None
    temperature: Optional[float] = None
    setpoint: Optional[float] = None
    duty: float = 0.0
    mode: ControlMode = ControlMode.AUTOMATIC
    updated_at: Optional[float] = None


class FanState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._status = FanStatus()

    def update(
        self,
        raw_temperature: float,
        temperature: float,
        setpoint: float,
        duty: float,
    ) -> None:
        with self._lock:
            self._status = FanStatus(
                raw_temperature=raw_temperature,
                temperature=temperature,
                setpoint=setpoint,
                duty=duty,
                mode=self._status.mode,
                updated_at=time(),
            )

    def set_mode(self, mode: ControlMode) -> FanStatus:
        with self._lock:
            current = self._status
            self._status = FanStatus(
                raw_temperature=current.raw_temperature,
                temperature=current.temperature,
                setpoint=current.setpoint,
                duty=current.duty,
                mode=mode,
                updated_at=current.updated_at,
            )
            return self._status

    def snapshot(self) -> FanStatus:
        with self._lock:
            return self._status
