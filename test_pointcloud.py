import numpy as np
import open3d as o3d

# Synthetic depth image: a surface 1 metre away
width, height = 640, 480
depth = np.full((height, width), 1.0, dtype=np.float32)

# Simulated camera intrinsics
fx = fy = 500.0
cx = width / 2
cy = height / 2

# Convert depth pixels into 3D camera-space coordinates
u, v = np.meshgrid(np.arange(width), np.arange(height))

z = depth
x = (u - cx) * z / fx
y = (v - cy) * z / fy

points = np.stack((x, -y, z), axis=-1).reshape(-1, 3)

cloud = o3d.geometry.PointCloud()
cloud.points = o3d.utility.Vector3dVector(points)

print(f"Generated {len(points):,} 3D points")
o3d.visualization.draw_geometries([cloud])
