from pathlib import Path

import numpy as np
import open3d as o3d


SCAN_DIR = Path("data/scans")


def create_test_terrain():
    """Generate a synthetic terrain for testing the 3D viewer."""
    x = np.linspace(-3, 3, 160)
    y = np.linspace(-3, 3, 160)
    xx, yy = np.meshgrid(x, y)

    z = (
        0.7 * np.exp(-((xx - 1.0)**2 + (yy - 0.5)**2))
        + 0.45 * np.exp(-((xx + 1.2)**2 + (yy + 0.8)**2))
        + 0.08 * np.sin(xx * 2) * np.cos(yy * 2)
    )

    points = np.column_stack((xx.ravel(), yy.ravel(), z.ravel()))

    # Colour the terrain by height.
    heights = (points[:, 2] - points[:, 2].min()) / (
        np.ptp(points[:, 2]) + 1e-9
    )
    colors = np.column_stack((
        0.15 + 0.75 * heights,
        0.25 + 0.45 * (1 - heights),
        0.65 - 0.40 * heights,
    ))

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    cloud.colors = o3d.utility.Vector3dVector(colors)
    return cloud


def load_scan():
    """Load the first supported scan found in data/scans."""
    files = sorted(
        list(SCAN_DIR.glob("*.ply"))
        + list(SCAN_DIR.glob("*.pcd"))
        + list(SCAN_DIR.glob("*.obj"))
    )

    if not files:
        print("No LiDAR scan found. Showing synthetic terrain instead.")
        return create_test_terrain(), "PHOTON | Synthetic Terrain"

    path = files[0]
    print(f"Loading scan: {path}")

    if path.suffix.lower() == ".obj":
        geometry = o3d.io.read_triangle_mesh(str(path))
        if not geometry.is_empty():
            geometry.compute_vertex_normals()
    else:
        geometry = o3d.io.read_point_cloud(str(path))

    if geometry.is_empty():
        raise RuntimeError(f"Could not load geometry from {path}")

    return geometry, f"PHOTON | {path.name}"


def main():
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    geometry, title = load_scan()

    print("\nPHOTON 3D Viewer")
    print("----------------")
    print("Mouse drag : rotate")
    print("Mouse wheel: zoom")
    print("Shift + drag: pan")
    print("Close window to exit.\n")

    o3d.visualization.draw_geometries(
        [geometry],
        window_name=title,
        width=1280,
        height=800,
    )


if __name__ == "__main__":
    main()
