import argparse
import logging

from fanpid.config import load_config
from fanpid.controller import FanController
from fanpid.fan import Fan
from fanpid.temperature import CpuTemperatureReader


def main() -> None:
    arguments = _parse_arguments()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",)

    config = load_config(arguments.config)
    fan = Fan(config.fan)
    controller = FanController(config, fan, CpuTemperatureReader(config.temperature.file))

    try:
        controller.run()
    except KeyboardInterrupt:
        fan.off()
        print("Fan stopped.")


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Raspberry Pi fan PID controller")
    parser.add_argument(
        "--config",
        default="config/fanpid.toml",
        help="path to the TOML configuration file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
