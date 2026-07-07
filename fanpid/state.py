from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Lock
from time import time
from typing import Optional


class ControlMode(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class ManualControlUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class FanStatus:
    raw_temperature: Optional[float] = None
    temperature: Optional[float] = None
    setpoint: Optional[float] = None
    duty: float = 0.0
    mode: ControlMode = ControlMode.AUTOMATIC
    manual_duty: Optional[float] = None
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
                manual_duty=self._status.manual_duty,
                updated_at=time(),
            )

    def set_mode(self, mode: ControlMode) -> FanStatus:
        with self._lock:
            current = self._status
            entering_manual_mode = (
                current.mode == ControlMode.AUTOMATIC
                and mode == ControlMode.MANUAL
            )
            self._status = FanStatus(
                raw_temperature=current.raw_temperature,
                temperature=current.temperature,
                setpoint=current.setpoint,
                duty=0.0 if entering_manual_mode else current.duty,
                mode=mode,
                manual_duty=(
                    0.0
                    if entering_manual_mode
                    else current.manual_duty if mode == ControlMode.MANUAL else None
                ),
                updated_at=current.updated_at,
            )
            return self._status

    def set_manual_duty(self, duty: float) -> FanStatus:
        with self._lock:
            current = self._status
            if current.mode != ControlMode.MANUAL:
                raise ManualControlUnavailableError(
                    "Manual fan duty can only be set in manual mode."
                )
            self._status = FanStatus(
                raw_temperature=current.raw_temperature,
                temperature=current.temperature,
                setpoint=current.setpoint,
                duty=current.duty,
                mode=current.mode,
                manual_duty=duty,
                updated_at=current.updated_at,
            )
            return self._status

    def snapshot(self) -> FanStatus:
        with self._lock:
            return self._status
