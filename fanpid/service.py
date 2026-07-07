from abc import ABC, abstractmethod

from fanpid.state import ControlMode, FanState, FanStatus


class FanControlService(ABC):
    @abstractmethod
    def get_status(self) -> FanStatus:
        """Return the current fan controller status."""

    @abstractmethod
    def set_mode(self, mode: ControlMode) -> FanStatus:
        """Change the fan control mode and return the updated status."""


class DefaultFanControlService(FanControlService):
    def __init__(self, state: FanState):
        self._state = state

    def get_status(self) -> FanStatus:
        return self._state.snapshot()

    def set_mode(self, mode: ControlMode) -> FanStatus:
        return self._state.set_mode(mode)
