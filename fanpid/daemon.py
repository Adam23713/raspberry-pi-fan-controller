import argparse
import logging
from threading import Thread

from fanpid.config import load_config
from fanpid.compose import DockerCliComposeServiceMonitorService
from fanpid.controller import FanController
from fanpid.fan import Fan
from fanpid.process import PsutilProcessMonitorService
from fanpid.service import DefaultFanControlService
from fanpid.state import FanState
from fanpid.temperature import FileCpuTemperatureReader
from fanpid.web import run_web_app


def main() -> None:
    arguments = _parse_arguments()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",)

    config = load_config(arguments.config)
    fan = Fan(config.fan)
    state = FanState()
    service = DefaultFanControlService(state)
    process_monitor_service = PsutilProcessMonitorService()
    compose_service_monitor = DockerCliComposeServiceMonitorService()
    controller = FanController(
        config,
        fan,
        FileCpuTemperatureReader(config.temperature.file),
        state,
    )

    if config.web.enabled:
        web_thread = Thread(
            target=run_web_app,
            args=(
                service,
                process_monitor_service,
                compose_service_monitor,
                config.web.host,
                config.web.port,
            ),
            name="fanpid-web",
            daemon=True,
        )
        web_thread.start()

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
