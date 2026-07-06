from fanpid.config import PidConfig


class PidController:
    def __init__(self, config: PidConfig):
        self._config = config
        self._integral = 0.0
        self._last_error = 0.0

    def calculate(self, temperature: float, previous_duty: float) -> float:
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
