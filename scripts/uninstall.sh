#!/usr/bin/env bash

set -euo pipefail

INSTALL_DIR="/opt/fanpid"
SERVICE_NAME="fanpid.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
PURGE=false

usage() {
    cat <<EOF
Usage: sudo ./scripts/uninstall.sh [--purge]

Without options, the service and virtual environment are removed while the
source code and configuration are preserved.

  --purge  Also remove ${INSTALL_DIR}, including its configuration and Git data
  --help   Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge)
            PURGE=true
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if [[ ${EUID} -ne 0 ]]; then
    echo "This uninstaller must be run as root." >&2
    echo "Try: sudo ./scripts/uninstall.sh" >&2
    exit 1
fi

echo "Uninstalling Raspberry Pi Fan Controller..."

if systemctl list-unit-files "${SERVICE_NAME}" --no-legend 2>/dev/null | grep -q "${SERVICE_NAME}"; then
    systemctl disable --now "${SERVICE_NAME}"
fi

rm -f "${SERVICE_FILE}"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true

if [[ "${PURGE}" == true ]]; then
    if [[ "${INSTALL_DIR}" != "/opt/fanpid" ]]; then
        echo "Refusing to purge unexpected install directory: ${INSTALL_DIR}" >&2
        exit 1
    fi

    rm -rf -- "${INSTALL_DIR}"
    echo "Removed ${INSTALL_DIR}, including its configuration and Git data."
else
    rm -rf -- "${INSTALL_DIR}/.venv"
    echo "Preserved source code and configuration in ${INSTALL_DIR}."
fi

echo "Uninstallation complete."
echo "System packages python3-venv and python3-lgpio were left installed."
