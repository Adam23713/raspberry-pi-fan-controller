#!/usr/bin/env bash

set -euo pipefail

INSTALL_DIR="/opt/fanpid"
SERVICE_NAME="fanpid.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [[ ${EUID} -ne 0 ]]; then
    echo "This installer must be run as root. Try: sudo ./scripts/install.sh" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required but was not found." >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "This installer currently supports Raspberry Pi OS and Debian-based systems." >&2
    echo "Install Python venv support and lgpio manually, then run it again." >&2
    exit 1
fi

if [[ ! -f "${PROJECT_DIR}/pyproject.toml" ]]; then
    echo "Could not find pyproject.toml in ${PROJECT_DIR}." >&2
    exit 1
fi

echo "Installing Raspberry Pi Fan Controller..."

echo "Installing system dependencies..."
if ! apt-get install -y python3-venv python3-lgpio; then
    echo "Refreshing package lists and retrying..."
    apt-get update
    apt-get install -y python3-venv python3-lgpio
fi

install -d -m 0755 "${INSTALL_DIR}"
install -d -m 0755 "${INSTALL_DIR}/config"

if [[ ! -f "${INSTALL_DIR}/config/fanpid.toml" ]]; then
    install -m 0644 \
        "${PROJECT_DIR}/config/fanpid.toml" \
        "${INSTALL_DIR}/config/fanpid.toml"
    echo "Installed default configuration."
else
    echo "Keeping existing configuration at ${INSTALL_DIR}/config/fanpid.toml."
fi

VENV_OPTIONS=(--system-site-packages)
if [[ -x "${INSTALL_DIR}/.venv/bin/python" ]]; then
    VENV_OPTIONS+=(--upgrade)
fi

if ! python3 -m venv "${VENV_OPTIONS[@]}" "${INSTALL_DIR}/.venv"; then
    echo "Failed to create or update the virtual environment." >&2
    exit 1
fi

"${INSTALL_DIR}/.venv/bin/pip" install --upgrade "${PROJECT_DIR}"

if ! "${INSTALL_DIR}/.venv/bin/python" -c "import lgpio"; then
    echo "The lgpio backend is not available inside the virtual environment." >&2
    exit 1
fi

install -m 0644 \
    "${PROJECT_DIR}/systemd/${SERVICE_NAME}" \
    "/etc/systemd/system/${SERVICE_NAME}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo
echo "Installation complete."
echo "Configuration: ${INSTALL_DIR}/config/fanpid.toml"
echo "Service status: sudo systemctl status ${SERVICE_NAME}"
echo "Live logs:      sudo journalctl -u ${SERVICE_NAME} -f"
