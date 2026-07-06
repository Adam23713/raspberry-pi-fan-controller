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

if [[ ! -f "${PROJECT_DIR}/pyproject.toml" ]]; then
    echo "Could not find pyproject.toml in ${PROJECT_DIR}." >&2
    exit 1
fi

echo "Installing Raspberry Pi Fan Controller..."

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

if [[ ! -x "${INSTALL_DIR}/.venv/bin/python" ]]; then
    if ! python3 -m venv "${INSTALL_DIR}/.venv"; then
        echo "Failed to create the virtual environment." >&2
        echo "Install the python3-venv package and run this script again." >&2
        exit 1
    fi
fi

"${INSTALL_DIR}/.venv/bin/pip" install --upgrade "${PROJECT_DIR}"

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
