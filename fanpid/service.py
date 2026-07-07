from abc import ABC, abstractmethod

from fanpid.state import (
    ControlMode,
    FanState,
    FanStatus,
    ManualControlUnavailableError,
)


class FanControlService(ABC):
    @abstractmethod
    def get_status(self) -> FanStatus:
        """Return the current fan controller status."""

    @abstractmethod
    def set_mode(self, mode: ControlMode) -> FanStatus:
        """Change the fan control mode and return the updated status."""

    @abstractmethod
    def set_manual_duty(self, duty: float) -> FanStatus:
        """Set the requested fan duty while manual mode is active."""


class DefaultFanControlService(FanControlService):
    def __init__(self, state: FanState):
        self._state = state

    def get_status(self) -> FanStatus:
        return self._state.snapshot()

    def set_mode(self, mode: ControlMode) -> FanStatus:
        return self._state.set_mode(mode)

    def set_manual_duty(self, duty: float) -> FanStatus:
        if not 0.0 <= duty <= 1.0:
            raise ValueError("Manual fan duty must be between 0.0 and 1.0.")
        return self._state.set_manual_duty(duty)
