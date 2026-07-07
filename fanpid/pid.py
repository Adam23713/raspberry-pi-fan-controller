from dataclasses import dataclass, replace
from math import isfinite
from threading import Lock

from fanpid.config import PidConfig


@dataclass(frozen=True)
class PidParameters:
    kp: float
    ki: float
    kd: float


class PidController:
    def __init__(self, config: PidConfig):
        self._config = config
        self._integral = 0.0
        self._last_error = 0.0
        self._lock = Lock()

    def calculate(self, temperature: float, previous_duty: float) -> float:
        with self._lock:
            return self._calculate(temperature, previous_duty)

    def get_parameters(self) -> PidParameters:
        with self._lock:
            return PidParameters(
                kp=self._config.kp,
                ki=self._config.ki,
                kd=self._config.kd,
            )

    def update_parameters(self, parameters: PidParameters) -> PidParameters:
        values = (parameters.kp, parameters.ki, parameters.kd)
        if any(not isfinite(value) or value < 0.0 for value in values):
            raise ValueError("PID parameters must be finite, non-negative numbers.")
        with self._lock:
            self._config = replace(
                self._config,
                kp=parameters.kp,
                ki=parameters.ki,
                kd=parameters.kd,
            )
            self._integral = 0.0
            self._last_error = 0.0
            return parameters

    def get_setpoint(self) -> float:
        with self._lock:
            return self._config.target_temp

    def _calculate(self, temperature: float, previous_duty: float) -> float:
        if temperature < self._config.fan_off_temp:
            self._integral = 0.0
            self._last_error = 0.0
            return 0.0

        if temperature >= self._config.full_speed_temp:
            self._integral = 0.0
            return 1.0

        error = temperature - self._config.target_temp

        if abs(error) <= self._config.deadband:
            return previous_duty

        self._integral += error * self._config.sample_time
        self._integral = _clamp(
            self._integral,
            -self._config.integral_limit,
            self._config.integral_limit,
        )

        derivative = (error - self._last_error) / self._config.sample_time
        output = (
            self._config.kp * error
            + self._config.ki * self._integral
            + self._config.kd * derivative
        )
        self._last_error = error
        return _clamp(output, 0.0, 1.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
