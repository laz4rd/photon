#!/usr/bin/env python3
"""Offline readiness checks for Photon; does not require an iPhone."""
import importlib
import shutil
import subprocess
import sys

def run(command):
    try:
        result = subprocess.run(
            command, check=False, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=5
        )
        return result.returncode, result.stdout.strip()
    except Exception as exc:
        return 127, str(exc)

print("PHOTON PREFLIGHT")
print("=" * 48)
print("Python:", sys.version.split()[0], sys.executable)

all_ok = True
for module in ("numpy", "cv2", "open3d", "record3d"):
    try:
        imported = importlib.import_module(module)
        version = getattr(imported, "__version__", "version n/a")
        print(f"[OK] import {module}: {version}")
    except Exception as exc:
        all_ok = False
        print(f"[FAIL] import {module}: {exc}")

for binary in ("idevice_id",):
    path = shutil.which(binary)
    if path:
        code, output = run([binary, "--version"])
        print(f"[OK] {binary}: {output or path}")
    else:
        all_ok = False
        print(f"[FAIL] {binary} not found in PATH")

code, output = run(["systemctl", "is-active", "usbmuxd.service"])
if code == 0 and output == "active":
    print("[OK] usbmuxd.service is active")
else:
    print(f"[WARN] usbmuxd.service state: {output or 'unknown'}")
    print("       If needed: sudo systemctl start usbmuxd.service")

try:
    from record3d import Record3DStream
    devices = Record3DStream.get_connected_devices()
    print(f"[INFO] Record3D USB devices visible now: {len(devices)}")
    for i, dev in enumerate(devices):
        print(f"       [{i}] product_id={dev.product_id}, udid={dev.udid}")
except Exception as exc:
    all_ok = False
    print(f"[FAIL] Record3D device discovery call: {exc}")

print("=" * 48)
if all_ok:
    print("Offline checks passed. Actual USB streaming still requires an iPhone and Record3D app.")
else:
    print("One or more checks failed. Fix those before presentation day.")
