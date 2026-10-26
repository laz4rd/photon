
import sys
from threading import Event

import cv2
import numpy as np
import open3d as o3d
from record3d import Record3DStream


class PhotonLive:
    def __init__(self):
        self.session = None
        self.frame_ready = Event()
        self.cloud = o3d.geometry.PointCloud()
        self.cloud_added = False

    def on_new_frame(self):
        # Called by Record3D on a background thread.
        # Keep this callback lightweight.
        self.frame_ready.set()

    def on_stream_stopped(self):
        print("Record3D stream stopped.")

    def connect(self):
        devices = Record3DStream.get_connected_devices()

        print(f"Found {len(devices)} connected iOS device(s).")

        if not devices:
            print(
                "\nNo iPhone detected.\n"
                "Connect the iPhone by USB, unlock it, "
                "and open the Record3D app."
            )
            return False

        for i, device in enumerate(devices):
            print(
                f"Device {i}: product_id={device.product_id}, "
                f"UDID={device.udid}"
            )

        self.session = Record3DStream()
        self.session.on_new_frame = self.on_new_frame
        self.session.on_stream_stopped = self.on_stream_stopped

        if not self.session.connect(devices[0]):
            print(
                "Connection failed. Check that Record3D is open "
                "and USB streaming is available."
            )
            return False

        print("Connected! Waiting for the first RGB-D frame...")
        return True

    def run(self):
        if not self.connect():
            return

        vis = o3d.visualization.Visualizer()
        vis.create_window("Photon | Live 3D", 960, 720)

        try:
            while True:
                if not self.frame_ready.wait(timeout=2):
                    if not vis.poll_events():
                        break
                    continue

                self.frame_ready.clear()

                # Copy the latest frames from Record3D.
                rgb = self.session.get_rgb_frame().copy()
                depth = self.session.get_depth_frame().copy()

                if rgb.size == 0 or depth.size == 0:
                    continue

                # Record3D provides RGB; OpenCV displays BGR.
                rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

                # Visualize depth in metres. Invalid/zero values
                # remain dark rather than being mistaken for distance.
                valid = np.isfinite(depth) & (depth > 0)
                depth_u8 = np.zeros(depth.shape, dtype=np.uint8)
                depth_u8[valid] = np.clip(
                    depth[valid] / 5.0 * 255, 0, 255
                ).astype(np.uint8)

                depth_view = cv2.applyColorMap(
                    depth_u8, cv2.COLORMAP_TURBO
                )
                depth_view[~valid] = (0, 0, 0)

                if np.any(valid):
                    median_depth = float(np.median(depth[valid]))
                    label = f"Valid depth median: {median_depth:.2f} m"
                else:
                    label = "No valid depth"

                cv2.putText(
                    depth_view, label, (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (255, 255, 255), 2,
                )

                # Match RGB colours to the depth map's resolution.
                dh, dw = depth.shape
                rgb_small = cv2.resize(
                    rgb, (dw, dh), interpolation=cv2.INTER_AREA
                )

                # Scale camera intrinsics to depth resolution.
                k = self.session.get_intrinsic_mat()
                rh, rw = rgb.shape[:2]
                sx = dw / rw
                sy = dh / rh

                fx = max(float(k.fx) * sx, 1e-6)
                fy = max(float(k.fy) * sy, 1e-6)
                cx = float(k.tx) * sx
                cy = float(k.ty) * sy

                # Sample every other depth pixel for a responsive viewer.
                step = 2
                vv, uu = np.mgrid[0:dh:step, 0:dw:step]
                z = depth[::step, ::step]
                colours = rgb_small[::step, ::step].astype(
                    np.float64
                ) / 255.0

                good = (
                    np.isfinite(z)
                    & (z > 0)
                    & (z < 10.0)
                )

                u = uu[good]
                v = vv[good]
                z = z[good]
                colours = colours[good]

                if len(z):
                    x = (u - cx) * z / fx
                    y = -(v - cy) * z / fy
                    points = np.column_stack((x, y, z))

                    self.cloud.points = o3d.utility.Vector3dVector(
                        points
                    )
                    self.cloud.colors = o3d.utility.Vector3dVector(
                        colours
                    )

                    if not self.cloud_added:
                        vis.add_geometry(self.cloud)
                        vis.reset_view_point(True)
                        self.cloud_added = True
                    else:
                        vis.update_geometry(self.cloud)

                cv2.imshow("Photon | Live RGB", rgb_bgr)
                cv2.imshow("Photon | Live Depth", depth_view)

                if not vis.poll_events():
                    break
                vis.update_renderer()

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        except KeyboardInterrupt:
            print("\nStopping Photon...")
        finally:
            self.session.disconnect()
            vis.destroy_window()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    PhotonLive().run()

