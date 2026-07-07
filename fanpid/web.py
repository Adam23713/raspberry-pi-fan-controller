from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from fanpid.service import FanControlService, ManualControlUnavailableError
from fanpid.state import ControlMode


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


def create_app(service: FanControlService) -> FastAPI:
    app = FastAPI(
        title="Raspberry Pi Fan Controller",
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return DASHBOARD_HTML

    @app.get("/api/status", response_model=FanStatusDto)
    def status() -> FanStatusDto:
        return _to_status_dto(service)

    @app.put("/api/mode", response_model=FanStatusDto)
    def set_mode(request: SetControlModeDto) -> FanStatusDto:
        service.set_mode(request.mode)
        return _to_status_dto(service)

    @app.put("/api/manual-duty", response_model=FanStatusDto)
    def set_manual_duty(request: SetManualDutyDto) -> FanStatusDto:
        try:
            service.set_manual_duty(request.duty)
        except ManualControlUnavailableError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _to_status_dto(service)

    return app


def run_web_app(service: FanControlService, host: str, port: int) -> None:
    uvicorn.run(
        create_app(service),
        host=host,
        port=port,
        log_level="info",
    )


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Raspberry Pi Fan Controller</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { margin: 0; background: #10151d; color: #e8edf4; }
    main { max-width: 1100px; margin: 0 auto; padding: 40px 20px; }
    h1 { margin: 0 0 8px; font-size: clamp(1.8rem, 5vw, 2.8rem); line-height: 1.15; overflow-wrap: anywhere; }
    .subtitle { margin: 0 0 32px; color: #91a0b5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap: 16px; }
    .card { min-width: 0; padding: 22px; border: 1px solid #293445; border-radius: 14px; background: #18202b; }
    .label { color: #91a0b5; font-size: .85rem; text-transform: uppercase; letter-spacing: .08em; }
    .value { margin-top: 10px; font-size: 2.2rem; font-weight: 700; }
    .unit { color: #91a0b5; font-size: 1rem; font-weight: 500; }
    .control { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; margin-top: 10px; }
    select, button { border: 1px solid #3a485d; border-radius: 8px; padding: 10px 12px; font: inherit; }
    select { flex: 1; background: #10151d; color: #e8edf4; }
    button { background: #3478c9; color: white; cursor: pointer; }
    button:disabled { cursor: wait; opacity: .65; }
    .mode-value { margin-top: 10px; font-size: 1.35rem; font-weight: 700; }
    .slider { width: 100%; margin: 16px 0 8px; accent-color: #3478c9; }
    .slider-row { display: flex; align-items: center; gap: 12px; }
    .slider-row output { min-width: 3.5em; text-align: right; font-weight: 700; }
    .control-status { min-height: 1.2em; margin-top: 8px; color: #91a0b5; font-size: .85rem; }
    .footer { margin-top: 24px; color: #91a0b5; font-size: .9rem; }
    .online { color: #65d69e; }
    .offline { color: #f2bd67; }
  </style>
</head>
<body>
  <main>
    <h1>Raspberry Pi Fan Controller</h1>
    <p class="subtitle">Live, read-only system status</p>
    <section class="grid">
      <article class="card">
        <div class="label">CPU temperature</div>
        <div class="value"><span id="temperature">--</span> <span class="unit">°C</span></div>
      </article>
      <article class="card">
        <div class="label">Raw temperature</div>
        <div class="value"><span id="raw-temperature">--</span> <span class="unit">°C</span></div>
      </article>
      <article class="card">
        <div class="label">Temperature setpoint</div>
        <div class="value"><span id="setpoint">--</span> <span class="unit">°C</span></div>
      </article>
      <article class="card">
        <div class="label">Fan PWM</div>
        <div class="value"><span id="duty">--</span> <span class="unit">%</span></div>
      </article>
      <article class="card">
        <div class="label">Current control mode</div>
        <div id="current-mode" class="mode-value">--</div>
      </article>
      <article class="card">
        <div class="label">Change control mode</div>
        <div class="control">
          <select id="mode">
            <option value="automatic">Automatic</option>
            <option value="manual">Manual</option>
          </select>
          <button id="apply-mode" type="button">Apply</button>
        </div>
        <div id="control-status" class="control-status"></div>
      </article>
      <article class="card">
        <div class="label">Manual fan PWM</div>
        <div class="slider-row">
          <input id="manual-duty" class="slider" type="range" min="0" max="100" step="1" value="0" disabled>
          <output id="manual-duty-value" for="manual-duty">0%</output>
        </div>
        <button id="apply-duty" type="button" disabled>Apply PWM</button>
        <div id="duty-status" class="control-status"></div>
      </article>
    </section>
    <p class="footer">
      Status: <span id="status" class="offline">Waiting for data</span>
      · Last update: <span id="updated-at">--</span>
    </p>
  </main>
  <script>
    const number = value => value == null ? "--" : value.toFixed(1);
    let manualDutyDirty = false;

    async function refresh() {
      const statusElement = document.getElementById("status");
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        document.getElementById("temperature").textContent = number(data.temperature);
        document.getElementById("raw-temperature").textContent = number(data.raw_temperature);
        document.getElementById("setpoint").textContent = number(data.setpoint);
        document.getElementById("duty").textContent = number(data.duty == null ? null : data.duty * 100);
        document.getElementById("current-mode").textContent = data.mode === "automatic"
          ? "Automatic"
          : "Manual";
        const manualMode = data.mode === "manual";
        document.getElementById("manual-duty").disabled = !manualMode;
        document.getElementById("apply-duty").disabled = !manualMode;
        if (manualMode && !manualDutyDirty && data.manual_duty != null) {
          const manualDutyPercent = Math.round(data.manual_duty * 100);
          document.getElementById("manual-duty").value = manualDutyPercent;
          document.getElementById("manual-duty-value").textContent = `${manualDutyPercent}%`;
        }
        document.getElementById("updated-at").textContent = data.updated_at == null
          ? "--"
          : new Date(data.updated_at * 1000).toLocaleString();
        statusElement.textContent = data.updated_at == null ? "Waiting for data" : "Online";
        statusElement.className = data.updated_at == null ? "offline" : "online";
      } catch (error) {
        statusElement.textContent = "Unavailable";
        statusElement.className = "offline";
      }
    }

    async function applyMode() {
      const button = document.getElementById("apply-mode");
      const controlStatus = document.getElementById("control-status");
      button.disabled = true;
      controlStatus.textContent = "Saving…";
      try {
        const response = await fetch("/api/mode", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: document.getElementById("mode").value }),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const manualMode = data.mode === "manual";
        document.getElementById("current-mode").textContent = manualMode ? "Manual" : "Automatic";
        document.getElementById("manual-duty").disabled = !manualMode;
        document.getElementById("apply-duty").disabled = !manualMode;
        if (manualMode) {
          document.getElementById("manual-duty").value = 0;
          document.getElementById("manual-duty-value").textContent = "0%";
          manualDutyDirty = false;
        }
        controlStatus.textContent = data.mode === "automatic"
          ? "Automatic PID control enabled"
          : "Manual mode enabled at 0% PWM";
      } catch (error) {
        controlStatus.textContent = "Could not change control mode";
      } finally {
        button.disabled = false;
      }
    }

    async function applyManualDuty() {
      const button = document.getElementById("apply-duty");
      const dutyStatus = document.getElementById("duty-status");
      const duty = Number(document.getElementById("manual-duty").value) / 100;
      button.disabled = true;
      dutyStatus.textContent = "Saving…";
      try {
        const response = await fetch("/api/manual-duty", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ duty }),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        manualDutyDirty = false;
        dutyStatus.textContent = `Manual PWM set to ${Math.round(duty * 100)}%`;
      } catch (error) {
        dutyStatus.textContent = "Could not set manual PWM";
      } finally {
        button.disabled = document.getElementById("current-mode").textContent !== "Manual";
      }
    }

    document.getElementById("apply-mode").addEventListener("click", applyMode);
    document.getElementById("manual-duty").addEventListener("input", event => {
      manualDutyDirty = true;
      document.getElementById("manual-duty-value").textContent = `${event.target.value}%`;
    });
    document.getElementById("apply-duty").addEventListener("click", applyManualDuty);
    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""
