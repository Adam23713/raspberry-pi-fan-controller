from abc import ABC, abstractmethod

from fanpid.state import FanState, FanStatus


class FanControlService(ABC):
    @abstractmethod
    def get_status(self) -> FanStatus:
        """Return the current fan controller status."""


class DefaultFanControlService(FanControlService):
    def __init__(self, state: FanState):
        self._state = state

    def get_status(self) -> FanStatus:
        return self._state.snapshot()
