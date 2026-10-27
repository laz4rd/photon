#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo "[Photon] Missing .venv. Create it and install dependencies first."
  exit 1
fi

source .venv/bin/activate
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

if command -v systemctl >/dev/null 2>&1 && ! systemctl is-active --quiet usbmuxd.service; then
  echo "[Photon] usbmuxd is not active; trying to start it..."
  if ! sudo systemctl start usbmuxd.service; then
    echo "[Photon] Could not start usbmuxd.service. Start it manually, then retry."
    exit 1
  fi
fi

echo "[Photon] Running preflight checks..."
python photon_preflight.py
echo
echo "[Photon] Starting live viewer..."
python photon_live.py
