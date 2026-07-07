import json
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class ComposeServiceInfo:
    name: str
    status: str
    cpu_percent: Optional[float]
    memory_bytes: Optional[int]
    uptime_seconds: Optional[int]


class ComposeServiceMonitorService(ABC):
    @abstractmethod
    def get_services(self) -> list[ComposeServiceInfo]:
        """Return containers belonging to Docker Compose services."""


class DockerCliComposeServiceMonitorService(ComposeServiceMonitorService):
    _COMPOSE_SERVICE_LABEL = "com.docker.compose.service"

    def get_services(self) -> list[ComposeServiceInfo]:
        try:
            container_ids = self._get_container_ids()
            if not container_ids:
                return []
            containers = self._inspect_containers(container_ids)
            statistics = self._get_statistics(container_ids)
        except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
            return []

        services = []
        for container in containers:
            config = container.get("Config", {})
            state = container.get("State", {})
            labels = config.get("Labels") or {}
            service_name = labels.get(self._COMPOSE_SERVICE_LABEL)
            if not service_name:
                continue

            container_name = container.get("Name", "").lstrip("/")
            stats = statistics.get(container_name, {})
            services.append(
                ComposeServiceInfo(
                    name=service_name,
                    status=str(state.get("Status", "unknown")).capitalize(),
                    cpu_percent=self._parse_percent(stats.get("CPUPerc")),
                    memory_bytes=self._parse_memory(stats.get("MemUsage")),
                    uptime_seconds=self._calculate_uptime(state),
                )
            )

        services.sort(key=lambda service: service.name.lower())
        return services

    def _get_container_ids(self) -> list[str]:
        result = self._run(
            [
                "docker",
                "ps",
                "--all",
                "--quiet",
                "--filter",
                f"label={self._COMPOSE_SERVICE_LABEL}",
            ]
        )
        return result.stdout.split()

    def _inspect_containers(self, container_ids: list[str]) -> list[dict]:
        result = self._run(["docker", "inspect", *container_ids])
        data = json.loads(result.stdout)
        if not isinstance(data, list):
            raise ValueError("Unexpected docker inspect response")
        return data

    def _get_statistics(self, container_ids: list[str]) -> dict[str, dict]:
        running_ids = self._get_running_container_ids()
        selected_ids = [container_id for container_id in container_ids if container_id in running_ids]
        if not selected_ids:
            return {}

        result = self._run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{json .}}",
                *selected_ids,
            ]
        )
        statistics = {}
        for line in result.stdout.splitlines():
            stats = json.loads(line)
            name = stats.get("Name")
            if name:
                statistics[name] = stats
        return statistics

    def _get_running_container_ids(self) -> set[str]:
        result = self._run(
            [
                "docker",
                "ps",
                "--quiet",
                "--filter",
                f"label={self._COMPOSE_SERVICE_LABEL}",
            ]
        )
        return set(result.stdout.split())

    @staticmethod
    def _run(command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )

    @staticmethod
    def _parse_percent(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        return float(value.strip().removesuffix("%"))

    @staticmethod
    def _parse_memory(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        amount = value.split("/", maxsplit=1)[0].strip()
        units = {
            "B": 1,
            "kB": 1000,
            "KB": 1000,
            "KiB": 1024,
            "MB": 1000**2,
            "MiB": 1024**2,
            "GB": 1000**3,
            "GiB": 1024**3,
        }
        for unit in sorted(units, key=len, reverse=True):
            if amount.endswith(unit):
                return int(float(amount[: -len(unit)].strip()) * units[unit])
        raise ValueError(f"Unknown memory unit: {amount}")

    @staticmethod
    def _calculate_uptime(state: dict) -> Optional[int]:
        if not state.get("Running"):
            return None
        started_at = state.get("StartedAt")
        if not started_at:
            return None
        normalized_started_at = re.sub(
            r"(\.\d{6})\d+",
            r"\1",
            started_at.replace("Z", "+00:00"),
        )
        started = datetime.fromisoformat(normalized_started_at)
        return max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
