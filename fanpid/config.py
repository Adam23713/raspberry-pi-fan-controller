from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclass(frozen=True)
class FanConfig:
    gpio: int
    pwm_frequency: int
    min_duty: float
    max_duty: float
    kickstart_duty: float
    kickstart_time: float
    max_pwm_step: float


@dataclass(frozen=True)
class TemperatureConfig:
    file: str
    average_samples: int


@dataclass(frozen=True)
class PidConfig:
    target_temp: float
    fan_off_temp: float
    full_speed_temp: float
    sample_time: float
    deadband: float
    kp: float
    ki: float
    kd: float
    integral_limit: float


@dataclass(frozen=True)
class LoggingConfig:
    interval: float
    pwm_delta: float


@dataclass(frozen=True)
class WebConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass(frozen=True)
class Config:
    fan: FanConfig
    temperature: TemperatureConfig
    pid: PidConfig
    logging: LoggingConfig
    web: WebConfig


def load_config(path: str | Path) -> Config:
    with Path(path).open("rb") as config_file:
        data = tomllib.load(config_file)

    return Config(
        fan=FanConfig(**data["fan"]),
        temperature=TemperatureConfig(**data["temperature"]),
        pid=PidConfig(**data["pid"]),
        logging=LoggingConfig(**data["logging"]),
        web=WebConfig(**data.get("web", {})),
    )
