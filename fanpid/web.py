from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fanpid.compose import ComposeServiceInfo, ComposeServiceMonitorService
from fanpid.process import ProcessInfo, ProcessMonitorService
from fanpid.service import FanControlService, ManualControlUnavailableError
from fanpid.state import ControlMode


FRONTEND_DIR = Path(__file__).with_name("frontend")
INDEX_HTML = FRONTEND_DIR / "index.html"


class FanStatusDto(BaseModel):
    raw_temperature: Optional[float] = None
    temperature: Optional[float] = None
    setpoint: Optional[float] = None
    duty: float
    mode: ControlMode
    manual_duty: Optional[float] = None
    updated_at: Optional[float] = None


class SetControlModeDto(BaseModel):
    mode: ControlMode


class SetManualDutyDto(BaseModel):
    duty: float


class ProcessDto(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_bytes: int


class ComposeServiceDto(BaseModel):
    name: str
    status: str
    cpu_percent: Optional[float] = None
    memory_bytes: Optional[int] = None
    uptime_seconds: Optional[int] = None


def _to_status_dto(service: FanControlService) -> FanStatusDto:
    current_status = service.get_status()
    return FanStatusDto(
        raw_temperature=current_status.raw_temperature,
        temperature=current_status.temperature,
        setpoint=current_status.setpoint,
        duty=current_status.duty,
        mode=current_status.mode,
        manual_duty=current_status.manual_duty,
        updated_at=current_status.updated_at,
    )


def _to_process_dto(process: ProcessInfo) -> ProcessDto:
    return ProcessDto(
        pid=process.pid,
        name=process.name,
        cpu_percent=process.cpu_percent,
        memory_percent=process.memory_percent,
        memory_bytes=process.memory_bytes,
    )


def _to_compose_service_dto(service: ComposeServiceInfo) -> ComposeServiceDto:
    return ComposeServiceDto(
        name=service.name,
        status=service.status,
        cpu_percent=service.cpu_percent,
        memory_bytes=service.memory_bytes,
        uptime_seconds=service.uptime_seconds,
    )


def create_app(
    fan_control_service: FanControlService,
    process_monitor_service: ProcessMonitorService,
    compose_service_monitor: ComposeServiceMonitorService,
) -> FastAPI:
    app = FastAPI(
        title="Raspberry Pi Fan Controller",
        docs_url=None,
        redoc_url=None,
    )
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    @app.get("/", response_class=FileResponse)
    def dashboard() -> FileResponse:
        return FileResponse(INDEX_HTML)

    @app.get("/api/status", response_model=FanStatusDto)
    def status() -> FanStatusDto:
        return _to_status_dto(fan_control_service)

    @app.get("/api/processes", response_model=list[ProcessDto])
    def processes() -> list[ProcessDto]:
        return [
            _to_process_dto(process)
            for process in process_monitor_service.get_top_processes(limit=5)
        ]

    @app.get("/api/compose-services", response_model=list[ComposeServiceDto])
    def compose_services() -> list[ComposeServiceDto]:
        return [
            _to_compose_service_dto(service)
            for service in compose_service_monitor.get_services()
        ]

    @app.put("/api/mode", response_model=FanStatusDto)
    def set_mode(request: SetControlModeDto) -> FanStatusDto:
        fan_control_service.set_mode(request.mode)
        return _to_status_dto(fan_control_service)

    @app.put("/api/manual-duty", response_model=FanStatusDto)
    def set_manual_duty(request: SetManualDutyDto) -> FanStatusDto:
        try:
            fan_control_service.set_manual_duty(request.duty)
        except ManualControlUnavailableError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _to_status_dto(fan_control_service)

    return app


def run_web_app(
    fan_control_service: FanControlService,
    process_monitor_service: ProcessMonitorService,
    compose_service_monitor: ComposeServiceMonitorService,
    host: str,
    port: int,
) -> None:
    uvicorn.run(
        create_app(
            fan_control_service,
            process_monitor_service,
            compose_service_monitor,
        ),
        host=host,
        port=port,
        log_level="info",
    )
