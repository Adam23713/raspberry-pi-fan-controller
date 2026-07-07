from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from fanpid.service import FanControlService


class FanStatusDto(BaseModel):
    raw_temperature: Optional[float] = None
    temperature: Optional[float] = None
    setpoint: Optional[float] = None
    duty: float
    updated_at: Optional[float] = None


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
        current_status = service.get_status()
        return FanStatusDto(
            raw_temperature=current_status.raw_temperature,
            temperature=current_status.temperature,
            setpoint=current_status.setpoint,
            duty=current_status.duty,
            updated_at=current_status.updated_at,
        )

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
    main { max-width: 900px; margin: 0 auto; padding: 48px 20px; }
    h1 { margin: 0 0 8px; font-size: clamp(1.8rem, 5vw, 2.8rem); }
    .subtitle { margin: 0 0 32px; color: #91a0b5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
    .card { padding: 22px; border: 1px solid #293445; border-radius: 14px; background: #18202b; }
    .label { color: #91a0b5; font-size: .85rem; text-transform: uppercase; letter-spacing: .08em; }
    .value { margin-top: 10px; font-size: 2.2rem; font-weight: 700; }
    .unit { color: #91a0b5; font-size: 1rem; font-weight: 500; }
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
    </section>
    <p class="footer">
      Status: <span id="status" class="offline">Waiting for data</span>
      · Last update: <span id="updated-at">--</span>
    </p>
  </main>
  <script>
    const number = value => value == null ? "--" : value.toFixed(1);

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

    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""
