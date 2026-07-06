# Raspberry Pi Fan Controller

A configurable PID-based fan controller for Raspberry Pi. It reads the CPU
temperature, smooths short temperature spikes, and controls a PWM fan through a
GPIO pin.

The project currently provides the fan-control daemon. A web dashboard, manual
control, process monitoring, and Docker Compose overview are planned.

## Features

- PID-based fan speed control
- Configurable target, fan-off, and full-speed temperatures
- Moving-average temperature filtering
- Deadband to prevent unnecessary speed changes
- Configurable PWM ramp rate
- Full-speed kickstart when the fan starts from rest
- Minimum and maximum duty-cycle limits
- Journal-friendly logging
- systemd service definition
- TOML configuration

## Requirements

- Raspberry Pi running Linux
- Python 3.9 or newer
- Python `venv` support (the `python3-venv` package on Raspberry Pi OS)
- PWM-capable fan control circuit

> [!WARNING]
> Do not connect a bare fan motor directly to a GPIO pin. Use a fan module with
> an integrated driver or a suitable external driver circuit.

## Tested hardware

This project is developed with the
[Argon Mini Fan for Raspberry Pi 4](https://malnapc.hu/custom/malnapc/image/data/docs/RS/A700000007741984.pdf).
The module includes its own controller board and connects directly to the
Raspberry Pi GPIO header.

For software-controlled operation:

1. Power off the Raspberry Pi before installing the fan.
2. Align the fan header with physical pins 1 through 12 as shown in the
   manufacturer's instructions.
3. Make sure the thermal pad and heatsink contact the CPU correctly.
4. Set the fan's hardware mode switch to `PWM`.

The manufacturer's standard configuration also uses **BCM GPIO 18**. This
project controls that pin continuously using software PWM instead of only
switching the fan at a fixed temperature.

The default configuration uses **BCM GPIO 18** at 100 Hz. Adjust these values to
match your wiring and hardware.

## Installation

The included systemd service expects the project at `/opt/fanpid`.

```bash
sudo git clone https://github.com/Adam23713/raspberry-pi-fan-controller.git /opt/fanpid
sudo /opt/fanpid/scripts/install.sh
```

The installer creates an isolated Python environment, installs the application,
copies and enables the systemd service, and starts the controller. An existing
`/opt/fanpid/config/fanpid.toml` file is preserved when the installer is run
again.

Check the service status and follow its logs with:

```bash
sudo systemctl status fanpid
sudo journalctl -u fanpid -f
```

## Running manually

For development or troubleshooting:

```bash
python3 -m venv .venv
.venv/bin/pip install .
sudo .venv/bin/fanpid --config config/fanpid.toml
```

Press `Ctrl+C` to stop the controller and turn the fan off.

## Configuration

Settings are stored in [`config/fanpid.toml`](config/fanpid.toml).

```toml
[fan]
gpio = 18
pwm_frequency = 100
min_duty = 0.30
max_duty = 1.0
kickstart_duty = 1.0
kickstart_time = 1.0
max_pwm_step = 0.05

[temperature]
file = "/sys/class/thermal/thermal_zone0/temp"
average_samples = 5

[pid]
target_temp = 50.0
fan_off_temp = 45.0
full_speed_temp = 70.0
sample_time = 2.0
deadband = 1.0
kp = 0.07
ki = 0.01
kd = 0.15
integral_limit = 20.0
```

Duty-cycle values use the range `0.0` to `1.0`. For example, `0.30` means
30% PWM duty cycle. Temperature values are in degrees Celsius, and time values
are in seconds.

After changing the configuration of a systemd installation, restart the
service:

```bash
sudo systemctl restart fanpid
```

## How it works

The controller samples the Raspberry Pi CPU temperature at a fixed interval and
calculates a moving average. Below `fan_off_temp`, the fan is turned off. At or
above `full_speed_temp`, it runs at the configured maximum duty cycle. Between
those limits, the PID controller calculates the requested output.

When starting from rest, the fan briefly receives `kickstart_duty` before
settling at the calculated speed. This helps fans that cannot start reliably at
a low PWM duty cycle.

## Project structure

```text
fanpid/
├── config.py       # TOML configuration models and loading
├── controller.py   # Main control loop
├── daemon.py       # Command-line entry point
├── fan.py          # GPIO/PWM fan access
├── pid.py          # PID calculation
└── temperature.py  # Raspberry Pi CPU temperature reader

config/fanpid.toml
systemd/fanpid.service
```

## Roadmap

- Safe shutdown and failsafe operation
- Automatic and manual control modes
- Web dashboard for temperature and fan status
- Web-based PID configuration
- Top CPU-consuming process overview
- Docker container and Compose project overview

## License

This project is licensed under the [MIT License](LICENSE).
