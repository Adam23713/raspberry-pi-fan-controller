const history = { temperature: [], raw: [], setpoint: [], duty: [] };
const colors = { temperature: "#35d069", raw: "#3d9cff", setpoint: "#9747ff", duty: "#f7bd3e" };
let manualDutyDirty = false;

const format = value => value == null ? "--" : Number(value).toFixed(1);
const push = (array, value) => { array.push(value); if (array.length > 90) array.shift(); };

function resizeCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width * ratio));
  const height = Math.max(1, Math.round(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
  return { ctx: canvas.getContext("2d"), width, height, ratio };
}

function drawLine(ctx, values, color, x, y, width, height, min, max) {
  if (values.length < 2) return;
  ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 2 * (window.devicePixelRatio || 1);
  values.forEach((value, index) => {
    const px = x + index * width / Math.max(1, values.length - 1);
    const py = y + height - (value - min) / Math.max(1, max - min) * height;
    index ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  });
  ctx.stroke();
}

function drawSpark(id, values, color) {
  const canvas = document.getElementById(id); const { ctx, width, height } = resizeCanvas(canvas);
  ctx.clearRect(0, 0, width, height); if (!values.length) return;
  const min = Math.min(...values) - 1; const max = Math.max(...values) + 1;
  drawLine(ctx, values, color, 0, 3, width, height - 6, min, max);
}

function drawHistory() {
  const canvas = document.getElementById("history-chart"); const { ctx, width, height, ratio } = resizeCanvas(canvas);
  ctx.clearRect(0, 0, width, height); const left = 44 * ratio, top = 16 * ratio, right = 16 * ratio, bottom = 28 * ratio;
  const chartWidth = width - left - right, chartHeight = height - top - bottom;
  ctx.font = `${11 * ratio}px system-ui`; ctx.fillStyle = "#91a1b4"; ctx.strokeStyle = "#1b2a38"; ctx.lineWidth = ratio;
  [0, 20, 40, 60, 80].forEach(value => { const y = top + chartHeight - value / 80 * chartHeight; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(left + chartWidth, y); ctx.stroke(); ctx.fillText(`${value} °C`, 0, y + 4 * ratio); });
  drawLine(ctx, history.temperature, colors.temperature, left, top, chartWidth, chartHeight, 0, 80);
  drawLine(ctx, history.raw, colors.raw, left, top, chartWidth, chartHeight, 0, 80);
  drawLine(ctx, history.setpoint, colors.setpoint, left, top, chartWidth, chartHeight, 0, 80);
}

function redrawCharts() {
  drawSpark("temp-spark", history.temperature, colors.temperature); drawSpark("raw-spark", history.raw, colors.raw);
  drawSpark("setpoint-spark", history.setpoint, colors.setpoint); drawSpark("duty-spark", history.duty, colors.duty); drawHistory();
}

function setOnline(online) {
  const text = online ? "Online" : "Unavailable";
  document.querySelector("#header-status span").textContent = text;
  document.getElementById("header-status").style.color = online ? "var(--green)" : "var(--yellow)";
}

function updateControlState(data) {
  const manual = data.mode === "manual";
  document.getElementById("current-mode").textContent = manual ? "Manual" : "Automatic";
  document.getElementById("current-mode").className = `mode-readout ${manual ? "purple" : "green"}`;
  document.getElementById("manual-duty").disabled = !manual; document.getElementById("apply-duty").disabled = !manual;
  if (manual && !manualDutyDirty && data.manual_duty != null) updateDutyControl(Math.round(data.manual_duty * 100));
}

function updateDutyControl(value) {
  document.getElementById("manual-duty").value = value; document.getElementById("manual-duty-value").textContent = `${value}%`;
  document.getElementById("gauge-value").textContent = `${value}%`; document.getElementById("gauge").style.setProperty("--duty", `${value * 1.8 - 90}deg`);
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" }); if (!response.ok) throw new Error(response.status);
    const data = await response.json();
    document.getElementById("temperature").textContent = format(data.temperature); document.getElementById("raw-temperature").textContent = format(data.raw_temperature);
    document.getElementById("setpoint").textContent = format(data.setpoint); document.getElementById("duty").textContent = format(data.duty == null ? null : data.duty * 100);
    updateControlState(data); setOnline(data.updated_at != null);
    if (data.temperature != null) push(history.temperature, data.temperature); if (data.raw_temperature != null) push(history.raw, data.raw_temperature);
    if (data.setpoint != null) push(history.setpoint, data.setpoint); push(history.duty, (data.duty || 0) * 100); redrawCharts();
  } catch (error) { setOnline(false); }
}

function createCell(text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  return cell;
}

function formatBytes(bytes) {
  if (bytes == null) return "–";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit < 2 ? 0 : 1)} ${units[unit]}`;
}

function getProcessIcon(processName) {
  const name = processName.toLowerCase();
  if (name.includes("fanpid")) return { symbol: "◉", type: "fanpid", label: "Fan PID" };
  if (name.includes("deluge") || name.includes("deloge")) return { symbol: "◆", type: "deluge", label: "Deluge" };
  if (name.includes("docker") || name.includes("containerd")) return { symbol: "▣", type: "docker", label: "Container" };
  if (name.includes("jellyfin")) return { symbol: "△", type: "jellyfin", label: "Jellyfin" };
  return { symbol: "⚙", type: "generic", label: "Process" };
}

function renderProcesses(processes) {
  const processList = document.getElementById("process-list");
  processList.replaceChildren();
  if (!processes.length) {
    const row = document.createElement("tr");
    const cell = createCell("No process data available", "muted-row");
    cell.colSpan = 4;
    row.append(cell);
    processList.append(row);
    return;
  }

  const maximumCpu = Math.max(1, ...processes.map(process => process.cpu_percent));
  processes.forEach(process => {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    const iconDefinition = getProcessIcon(process.name);
    const content = document.createElement("span");
    const icon = document.createElement("span");
    const processName = document.createElement("span");
    name.className = "process";
    name.title = `PID ${process.pid}`;
    content.className = "process-content";
    icon.className = `process-icon ${iconDefinition.type}`;
    icon.textContent = iconDefinition.symbol;
    icon.title = iconDefinition.label;
    processName.textContent = process.name;
    content.append(icon, processName);
    name.append(content);

    const cpu = document.createElement("td");
    const bar = document.createElement("span");
    const fill = document.createElement("i");
    bar.className = "bar";
    fill.style.setProperty("--w", `${process.cpu_percent / maximumCpu * 100}%`);
    bar.append(fill);
    cpu.append(bar, `${process.cpu_percent.toFixed(1)}%`);

    row.append(
      name,
      cpu,
      createCell(`${process.memory_percent.toFixed(1)}%`),
      createCell(formatBytes(process.memory_bytes)),
    );
    processList.append(row);
  });
}

async function refreshProcesses() {
  try {
    const response = await fetch("/api/processes", { cache: "no-store" });
    if (!response.ok) throw new Error(response.status);
    renderProcesses(await response.json());
  } catch (error) {
    const processList = document.getElementById("process-list");
    processList.replaceChildren();
    const row = document.createElement("tr");
    const cell = createCell("Process data unavailable", "muted-row");
    cell.colSpan = 4;
    row.append(cell);
    processList.append(row);
  }
}

function formatDuration(seconds) {
  if (seconds == null) return "–";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor(seconds % 86400 / 3600);
  const minutes = Math.floor(seconds % 3600 / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return [
    days ? `${days}d` : null,
    `${hours}h`,
    `${minutes}m`,
    `${remainingSeconds}s`,
  ].filter(Boolean).join(" ");
}

function renderComposeServices(services) {
  const serviceList = document.getElementById("compose-service-list");
  serviceList.replaceChildren();
  if (!services.length) {
    const row = document.createElement("tr");
    const cell = createCell("No Docker Compose services found", "muted-row");
    cell.colSpan = 5;
    row.append(cell);
    serviceList.append(row);
    return;
  }

  services.forEach(service => {
    const row = document.createElement("tr");
    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `badge${service.status.toLowerCase() === "running" ? "" : " stopped"}`;
    badge.textContent = service.status;
    statusCell.append(badge);
    row.append(
      createCell(service.name),
      statusCell,
      createCell(service.cpu_percent == null ? "–" : `${service.cpu_percent.toFixed(1)}%`),
      createCell(formatBytes(service.memory_bytes)),
      createCell(formatDuration(service.uptime_seconds)),
    );
    serviceList.append(row);
  });
}

async function refreshComposeServices() {
  try {
    const response = await fetch("/api/compose-services", { cache: "no-store" });
    if (!response.ok) throw new Error(response.status);
    renderComposeServices(await response.json());
  } catch (error) {
    const serviceList = document.getElementById("compose-service-list");
    serviceList.replaceChildren();
    const row = document.createElement("tr");
    const cell = createCell("Docker Compose data unavailable", "muted-row");
    cell.colSpan = 5;
    row.append(cell);
    serviceList.append(row);
  }
}

async function applyMode() {
  const button = document.getElementById("apply-mode"), message = document.getElementById("control-status"); button.disabled = true; message.textContent = "Saving…";
  try { const response = await fetch("/api/mode", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: document.getElementById("mode").value }) }); if (!response.ok) throw new Error(response.status); const data = await response.json(); manualDutyDirty = false; updateControlState(data); if (data.mode === "manual") updateDutyControl(0); message.textContent = "Mode updated"; }
  catch (error) { message.textContent = "Could not change mode"; } finally { button.disabled = false; }
}

async function applyDuty() {
  const button = document.getElementById("apply-duty"), message = document.getElementById("duty-status"), duty = Number(document.getElementById("manual-duty").value) / 100; button.disabled = true; message.textContent = "Saving…";
  try { const response = await fetch("/api/manual-duty", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ duty }) }); if (!response.ok) throw new Error(response.status); manualDutyDirty = false; message.textContent = "PWM updated"; }
  catch (error) { message.textContent = "Could not set PWM"; } finally { button.disabled = document.getElementById("current-mode").textContent !== "Manual"; }
}

function updateClock() { document.getElementById("clock").textContent = new Date().toLocaleString(); }

document.getElementById("apply-mode").addEventListener("click", applyMode); document.getElementById("apply-duty").addEventListener("click", applyDuty);
document.getElementById("manual-duty").addEventListener("input", event => { manualDutyDirty = true; updateDutyControl(event.target.value); });
window.addEventListener("resize", redrawCharts); updateClock(); refresh(); refreshProcesses(); refreshComposeServices(); setInterval(updateClock, 1000); setInterval(refresh, 2000); setInterval(refreshProcesses, 5000); setInterval(refreshComposeServices, 10000);
