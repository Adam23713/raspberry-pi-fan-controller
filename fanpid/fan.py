import time

from gpiozero import PWMOutputDevice

from fanpid.config import FanConfig


class Fan:
    def __init__(self, config: FanConfig):
        self._config = config
        self._device = PWMOutputDevice(config.gpio, frequency=config.pwm_frequency)

    def set_duty(self, duty: float) -> None:
        self._device.value = duty

    def kickstart(self) -> None:
        self.set_duty(self._config.kickstart_duty)
        time.sleep(self._config.kickstart_time)

    def off(self) -> None:
        self._device.off()
