import logging
import time
from collections import deque

from fanpid.config import Config
from fanpid.fan import Fan
from fanpid.pid import PidController
from fanpid.state import FanState
from fanpid.temperature import CpuTemperatureReader


class FanController:
    def __init__(
        self,
        config: Config,
        fan: Fan,
        temperature_reader: CpuTemperatureReader,
        state: FanState,
    ):
        self._config = config
        self._fan = fan
        self._temperature_reader = temperature_reader
        self._state = state
        self._pid = PidController(config.pid)
        self._temperatures: deque[float] = deque(
            maxlen=config.temperature.average_samples
        )
        self._previous_duty = 0.0
        self._last_log_time = time.monotonic()
        self._last_logged_duty = 0.0
        self._logger = logging.getLogger("fanpid")

    def run(self) -> None:
        while True:
            raw_temperature = self._temperature_reader.read()
            self._temperatures.append(raw_temperature)
            temperature = sum(self._temperatures) / len(self._temperatures)

            duty = self._pid.calculate(temperature, self._previous_duty)
            if duty > 0.0:
                duty = max(duty, self._config.fan.min_duty)
            duty = min(duty, self._config.fan.max_duty)

            starting_fan = self._previous_duty == 0.0 and duty > 0.0
            if starting_fan:
                self._logger.info(
                    "Starting fan with %.0f%% PWM for %.1f s",
                    self._config.fan.kickstart_duty * 100,
                    self._config.fan.kickstart_time,
                )
                self._fan.kickstart()
            else:
                duty = self._limit_pwm_step(duty)

            self._fan.set_duty(duty)
            self._previous_duty = duty
            self._state.update(raw_temperature, temperature, duty)
            self._log_status(temperature, raw_temperature, duty)
            time.sleep(self._config.pid.sample_time)

    def _limit_pwm_step(self, new_duty: float) -> float:
        delta = new_duty - self._previous_duty
        max_step = self._config.fan.max_pwm_step
        if delta > max_step:
            return self._previous_duty + max_step
        if delta < -max_step:
            return self._previous_duty - max_step
        return new_duty

    def _log_status(
        self,
        temperature: float,
        raw_temperature: float,
        duty: float,
    ) -> None:
        now = time.monotonic()
        log_config = self._config.logging
        if (
            now - self._last_log_time >= log_config.interval
            or abs(duty - self._last_logged_duty) >= log_config.pwm_delta
        ):
            self._logger.info(
                "CPU: %.1f °C (raw: %.1f °C) | Fan PWM: %.0f%%",
                temperature,
                raw_temperature,
                duty * 100,
            )
            self._last_log_time = now
            self._last_logged_duty = duty
