#!/usr/bin/env python3
"""Photon live RGB-D viewer for the Record3D iOS USB stream.

Views:
  1. Live RGB image
  2. Colour-coded depth map with a centre-point distance estimate
  3. Live coloured 3D point cloud

Depth values are treated as metres, as returned by the Record3D stream.
This app visualizes processed depth; it does not expose raw LiDAR pulse timing.
"""
from __future__ import annotations

import sys
import time
from threading import Event

import cv2
import numpy as np
import open3d as o3d
from record3d import Record3DStream

DEVICE_TYPE_TRUEDEPTH = 0
DEVICE_TYPE_LIDAR = 1
MAX_DEPTH_M = 6.0
POINT_STRIDE = 3


class PhotonLive:
    def __init__(self) -> None:
        self.session = None
        self.frame_ready = Event()
        self.stream_stopped = Event()
        self.cloud = o3d.geometry.PointCloud()
        self.cloud_added = False
        self.last_frame_time = 0.0
        self.frame_count = 0

    def on_new_frame(self) -> None:
        # Record3D calls this on its worker thread. Keep it lightweight.
        self.frame_ready.set()

    def on_stream_stopped(self) -> None:
        print("\n[Photon] Record3D reports that the stream stopped.")
        self.stream_stopped.set()
        self.frame_ready.set()

    @staticmethod
    def print_device(device, index: int) -> None:
        print(
            f"  [{index}] product_id={device.product_id} "
            f"udid={device.udid}"
        )

    def connect(self) -> bool:
        print("[Photon] Looking for Record3D USB devices...")
        try:
            devices = Record3DStream.get_connected_devices()
        except Exception as exc:
            print(f"[ERROR] Device discovery failed: {exc}")
            print("Check the USB cable, unlock the iPhone, and open Record3D.")
            return False

        print(f"[Photon] Found {len(devices)} device(s).")
        if not devices:
            print(
                "\nNo Record3D-compatible device was detected.\n"
                "On the iPhone:\n"
                "  1. Connect with a data-capable USB cable and unlock it.\n"
                "  2. Open Record3D and allow the computer connection if prompted.\n"
                "  3. Settings > Live RGBD Video Streaming > USB.\n"
                "  4. Return to Record/stream screen and press the red start button.\n"
                "Then run ./run_photon.sh again.\n"
            )
            return False

        for i, device in enumerate(devices):
            self.print_device(device, i)

        self.session = Record3DStream()
        self.session.on_new_frame = self.on_new_frame
        self.session.on_stream_stopped = self.on_stream_stopped

        try:
            connected = self.session.connect(devices[0])
        except Exception as exc:
            print(f"[ERROR] Record3D connection raised an exception: {exc}")
            self.session = None
            return False

        if connected is False:
            print(
                "[ERROR] Record3D could not start the stream. "
                "Check the app's USB streaming setting and press its start button."
            )
            try:
                self.session.disconnect()
            except Exception:
                pass
            self.session = None
            return False

        print("[Photon] Connected. Waiting for RGB-D frames...")
        return True

    @staticmethod
    def prepare_depth(depth: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        depth = np.asarray(depth, dtype=np.float32)
        valid = np.isfinite(depth) & (depth > 0) & (depth <= MAX_DEPTH_M)
        return depth, valid

    @staticmethod
    def get_intrinsics(session, rgb_shape, depth_shape):
        coeffs = session.get_intrinsic_mat()
        rgb_h, rgb_w = rgb_shape[:2]
        depth_h, depth_w = depth_shape[:2]
        sx = depth_w / float(rgb_w)
        sy = depth_h / float(rgb_h)
        fx = max(float(coeffs.fx) * sx, 1e-6)
        fy = max(float(coeffs.fy) * sy, 1e-6)
        cx = float(coeffs.tx) * sx
        cy = float(coeffs.ty) * sy
        return fx, fy, cx, cy

    def make_point_cloud(self, rgb: np.ndarray, depth: np.ndarray):
        depth_h, depth_w = depth.shape[:2]
        rgb_small = cv2.resize(rgb, (depth_w, depth_h), interpolation=cv2.INTER_AREA)

        fx, fy, cx, cy = self.get_intrinsics(
            self.session, rgb.shape, depth.shape
        )

        v_grid, u_grid = np.mgrid[
            0:depth_h:POINT_STRIDE, 0:depth_w:POINT_STRIDE
        ]
        z_grid = depth[::POINT_STRIDE, ::POINT_STRIDE]
        colours_grid = rgb_small[::POINT_STRIDE, ::POINT_STRIDE]

        valid = (
            np.isfinite(z_grid)
            & (z_grid > 0)
            & (z_grid <= MAX_DEPTH_M)
        )
        if not np.any(valid):
            return None, None

        u = u_grid[valid].astype(np.float32)
        v = v_grid[valid].astype(np.float32)
        z = z_grid[valid].astype(np.float32)
        colours = colours_grid[valid].astype(np.float32) / 255.0

        x = (u - cx) * z / fx
        y = -(v - cy) * z / fy
        points = np.column_stack((x, y, z)).astype(np.float64)
        return points, colours.astype(np.float64)

    def run(self) -> int:
        if not self.connect():
            return 2

        vis = o3d.visualization.Visualizer()
        if not vis.create_window("Photon | Live 3D Point Cloud", 1000, 760):
            print("[ERROR] Open3D could not create a window.")
            try:
                self.session.disconnect()
            except Exception:
                pass
            return 3

        print("[Photon] Press Q in an OpenCV window or close the 3D window to quit.")
        print("[Photon] Centre distance is an estimate from the centre depth pixel.")
        last_no_frame_warning = time.monotonic()

        try:
            while True:
                if self.stream_stopped.is_set():
                    break

                # Process at most the latest frame, avoiding a backlog.
                got_frame = self.frame_ready.wait(timeout=0.25)
                if not got_frame:
                    if not vis.poll_events():
                        break
                    now = time.monotonic()
                    if now - last_no_frame_warning > 8:
                        print("[Photon] Still waiting for frames. Is streaming started in Record3D?")
                        last_no_frame_warning = now
                    continue

                self.frame_ready.clear()

                try:
                    rgb = np.asarray(self.session.get_rgb_frame()).copy()
                    depth = np.asarray(self.session.get_depth_frame()).copy()
                    confidence = np.asarray(self.session.get_confidence_frame()).copy()
                    device_type = int(self.session.get_device_type())
                except Exception as exc:
                    print(f"[WARNING] Could not read a frame: {exc}")
                    continue

                if rgb.ndim != 3 or rgb.shape[2] < 3 or depth.ndim != 2:
                    print(f"[WARNING] Unexpected frame shapes: RGB={rgb.shape}, depth={depth.shape}")
                    continue

                rgb = rgb[:, :, :3]
                depth, valid = self.prepare_depth(depth)

                # Record3D RGB data is RGB; OpenCV's display expects BGR.
                rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                if device_type == DEVICE_TYPE_TRUEDEPTH:
                    # Record3D's sample mirrors TrueDepth frames; LiDAR frames are not flipped.
                    rgb_bgr = cv2.flip(rgb_bgr, 1)
                    depth = cv2.flip(depth, 1)
                    valid = cv2.flip(valid.astype(np.uint8), 1).astype(bool)
                elif device_type != DEVICE_TYPE_LIDAR:
                    pass

                depth_u8 = np.zeros(depth.shape, dtype=np.uint8)
                depth_u8[valid] = np.clip(
                    depth[valid] / MAX_DEPTH_M * 255.0, 0, 255
                ).astype(np.uint8)
                depth_view = cv2.applyColorMap(depth_u8, cv2.COLORMAP_TURBO)
                depth_view[~valid] = (0, 0, 0)

                dh, dw = depth.shape
                cy, cx = dh // 2, dw // 2
                if valid[cy, cx]:
                    centre_m = float(depth[cy, cx])
                    centre_label = f"Centre depth: {centre_m:.2f} m"
                    # Draw the sample location on the depth map.
                    cv2.drawMarker(
                        depth_view, (cx, cy), (255, 255, 255),
                        markerType=cv2.MARKER_CROSS, markerSize=18, thickness=2
                    )
                else:
                    centre_label = "Centre depth: invalid"
                cv2.putText(
                    depth_view, centre_label, (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
                    cv2.LINE_AA
                )

                points, colours = self.make_point_cloud(rgb, depth)
                if points is not None and len(points):
                    self.cloud.points = o3d.utility.Vector3dVector(points)
                    self.cloud.colors = o3d.utility.Vector3dVector(colours)
                    if not self.cloud_added:
                        vis.add_geometry(self.cloud)
                        vis.reset_view_point(True)
                        self.cloud_added = True
                    else:
                        vis.update_geometry(self.cloud)

                if confidence.size:
                    confidence_view = confidence
                    if confidence_view.ndim == 2:
                        confidence_view = np.clip(
                            confidence_view.astype(np.float32) / 2.0 * 255,
                            0, 255
                        ).astype(np.uint8)
                    cv2.imshow("Photon | Confidence", confidence_view)

                cv2.imshow("Photon | Live RGB", rgb_bgr)
                cv2.imshow("Photon | Live Depth", depth_view)

                if not vis.poll_events():
                    break
                vis.update_renderer()
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break

                self.frame_count += 1
                self.last_frame_time = time.monotonic()

        except KeyboardInterrupt:
            print("\n[Photon] Stopping...")
        finally:
            try:
                self.session.disconnect()
            except Exception:
                pass
            vis.destroy_window()
            cv2.destroyAllWindows()

        print(f"[Photon] Frames processed: {self.frame_count}")
        return 0


if __name__ == "__main__":
    raise SystemExit(PhotonLive().run())
