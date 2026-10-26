import cv2
import numpy as np
import open3d as o3d

# Photon: synthetic RGB-D capture simulator
W, H = 640, 480
FX = FY = 500.0
CX, CY = W / 2, H / 2

# Open3D visualizer
vis = o3d.visualization.Visualizer()
vis.create_window("Photon | 3D Point Cloud", W, H)

cloud = o3d.geometry.PointCloud()

# Add a small initial point cloud so Open3D can set up its view.
cloud.points = o3d.utility.Vector3dVector(
    np.array([
        [-0.5, -0.5, 1.0],
        [ 0.5, -0.5, 1.0],
        [-0.5,  0.5, 1.0],
        [ 0.5,  0.5, 1.0],
    ])
)
cloud.colors = o3d.utility.Vector3dVector(
    np.array([
        [1.0, 0.2, 0.2],
        [0.2, 1.0, 0.2],
        [0.2, 0.2, 1.0],
        [1.0, 1.0, 1.0],
    ])
)

vis.add_geometry(cloud)
vis.reset_view_point(True)

points_per_frame = 40 * 30
u, v = np.meshgrid(
    np.linspace(0, W - 1, 40),
    np.linspace(0, H - 1, 30),
)
u, v = u.ravel(), v.ravel()

print("Photon simulator started.")
print("Press Q in the RGB window to quit.")

frame = 0

while True:
    # Synthetic RGB image
    rgb = np.zeros((H, W, 3), dtype=np.uint8)
    rgb[:] = (28, 28, 28)

    # Moving object
    x = int(220 + 120 * np.sin(frame * 0.04))
    y = 180
    cv2.rectangle(rgb, (x, y), (x + 120, y + 120), (255, 180, 40), -1)

    # Synthetic depth: background at 2 m, object oscillates
    depth = np.full((H, W), 2.0, dtype=np.float32)
    distance = 0.8 + 0.5 * (1 + np.sin(frame * 0.04))
    depth[y:y + 120, x:x + 120] = distance

    # Colour-coded depth map
    depth_u8 = np.clip(depth / 3.0 * 255, 0, 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(depth_u8, cv2.COLORMAP_TURBO)

    cv2.putText(
        heatmap, f"SIMULATED DEPTH: {distance:.2f} m",
        (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
        (255, 255, 255), 2,
    )

    # Reconstruct sampled 3D points
    ui = np.clip(u.astype(int), 0, W - 1)
    vi = np.clip(v.astype(int), 0, H - 1)
    z = depth[vi, ui]

    px = (u - CX) * z / FX
    py = -(v - CY) * z / FY
    pts = np.column_stack((px, py, z))

    # Colour points using their corresponding RGB pixels
    colors = rgb[vi, ui].astype(np.float64) / 255.0

    cloud.points = o3d.utility.Vector3dVector(pts)
    cloud.colors = o3d.utility.Vector3dVector(colors)

    vis.update_geometry(cloud)
    vis.poll_events()
    vis.update_renderer()

    cv2.imshow("Photon | RGB", rgb)
    cv2.imshow("Photon | Depth", heatmap)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q") or not vis.poll_events():
        break

    frame += 1

vis.destroy_window()
cv2.destroyAllWindows()
