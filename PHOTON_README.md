# Photon — live iPhone RGB-D / LiDAR visualizer

Photon displays Record3D's processed RGB-D stream in three views:

1. **Live RGB** — camera colour feed.
2. **Live depth** — colour-coded depth map and centre-pixel depth estimate.
3. **Live 3D point cloud** — coloured points reconstructed from depth and camera intrinsics.
4. **Confidence** — confidence map when supplied by the installed Record3D library.

> This visualizes the processed depth map from the iPhone app. It does not directly expose raw LiDAR pulse timings or independently measure time-of-flight.

## Offline readiness check

From the project directory:

```bash
source .venv/bin/activate
python -m py_compile photon_live.py photon_preflight.py
python photon_preflight.py
```

No iPhone is required for these checks. A device count of zero is expected until an iPhone is connected and streaming.

## Presentation-day steps

1. Connect an iPhone Pro with a **data-capable USB cable** and unlock it.
2. Open **Record3D** on the iPhone.
3. In Record3D Settings, enable **Live RGBD Video Streaming → USB**.
4. Return to the Record/stream screen and press the red start/record toggle to start streaming.
5. On the Arch Linux laptop, from `~/photon`, run:

   ```bash
   ./run_photon.sh
   ```

6. If the stream does not start, check the USB cable, unlock/trust prompt, and that streaming is actively started in the app.
7. Press `q` in an OpenCV window to quit.

Record3D documents USB live streaming as a paid feature. Confirm that the app/account has USB streaming enabled before presentation day.

## Troubleshooting

### `idevice_id -l` prints nothing
- Try another USB data cable/port.
- Unlock the phone and accept any Trust prompt.
- Start the daemon if needed: `sudo systemctl start usbmuxd.service`.

### Linux detects the iPhone but Record3D reports zero devices
- Ensure Record3D is open and USB streaming mode is enabled.
- Start streaming in the app (red toggle).
- Re-run `python photon_preflight.py`.

### `connect()` fails
- Make sure only the intended iPhone is connected.
- Recheck the app's USB streaming mode and active stream.
- Try unplugging/replugging after unlocking the phone.

### OpenCV says Qt Wayland plugin is missing
Use the included launcher, which defaults to `QT_QPA_PLATFORM=xcb`.

### Empty/black depth map
Depth pixels may be invalid or outside the displayed 0–6 m range. Move the phone toward a textured, well-lit scene and check the confidence window.

## Files

- `photon_live.py` — real Record3D viewer.
- `photon_preflight.py` — offline checks and USB device discovery.
- `run_photon.sh` — launcher.
- `photon_sim.py` — keep your already-working simulator as a fallback; this bundle does not replace it.
