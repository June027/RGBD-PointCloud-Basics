"""Experiment 01: aligned RGB-D -> camera-frame colored point cloud.

Default input is SYNTHETIC: a red square face at 1 m and a wall at 2 m.
No detector, simulator, model, or real sensor is used. Requires numpy and Pillow.
"""
from pathlib import Path
import base64
import io
import json

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent / "results"


def make_rgbd():
    width, height = 320, 240
    # Camera convention: +X right, +Y down, +Z forward. Depth is optical-axis Z.
    fx = fy = 300.0
    cx, cy = 160.0, 120.0
    v, u = np.indices((height, width))
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    checker = ((u // 20 + v // 20) % 2).astype(bool)
    rgb[:] = [180, 195, 205]
    rgb[checker] = [130, 155, 175]
    depth_mm = np.full((height, width), 2000, dtype=np.uint16)
    # This mask is manually specified ground truth, NOT model output.
    target = (u >= 130) & (u <= 190) & (v >= 90) & (v <= 150)
    rgb[target] = [230, 65, 60]
    depth_mm[target] = 1000
    return rgb, depth_mm, (fx, fy, cx, cy), target


def depth_to_pointcloud(rgb, depth_raw, intrinsics, depth_scale=1000.0):
    """Back-project aligned pixels. depth_scale is raw depth units per meter."""
    fx, fy, cx, cy = intrinsics
    v, u = np.indices(depth_raw.shape)
    z = depth_raw.astype(np.float64) / depth_scale
    valid = np.isfinite(z) & (z > 0)
    x = (u - cx) * z / fx
    y = (v - cy) * z / fy
    points = np.stack((x, y, z), axis=-1)
    return points[valid], rgb[valid], points


def png_uri(array):
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rgb, depth_mm, intrinsics, target = make_rgbd()
    points, colors, organized = depth_to_pointcloud(rgb, depth_mm, intrinsics)
    Image.fromarray(rgb).save(OUT / "rgb.png")
    # Preserve actual 16-bit millimeter values; depth_preview is display-only.
    Image.fromarray(depth_mm).save(OUT / "depth_mm.png")
    preview = np.uint8(depth_mm.astype(float) / 2000 * 255)
    Image.fromarray(preview).save(OUT / "depth_preview.png")
    np.save(OUT / "points_camera_m.npy", points)
    with (OUT / "cloud.ply").open("w", encoding="ascii") as f:
        f.write("ply\nformat ascii 1.0\nelement vertex " + str(len(points)) +
                "\nproperty float x\nproperty float y\nproperty float z\n"
                "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
        np.savetxt(f, np.column_stack((points, colors)), fmt="%.6f %.6f %.6f %d %d %d")

    # Independent scene expectations: optical center ray and known target width.
    center = organized[120, 160]
    measured_width = np.ptp(organized[target, 0])
    assert np.allclose(center, [0, 0, 1]), center
    assert np.isclose(measured_width, 0.2), measured_width
    assert np.isclose(organized[0, 0, 2], 2.0)
    # Off-axis depth is NOT Euclidean distance from the camera.
    edge = organized[120, 190]
    summary = {
        "data_source": "synthetic; hand-specified red face and wall",
        "frame": "+X right, +Y down, +Z forward; meters",
        "intrinsics_fx_fy_cx_cy": intrinsics,
        "depth_scale_raw_units_per_meter": 1000,
        "point_count": len(points),
        "center_pixel_uv": [160, 120],
        "center_point_xyz_m": center.tolist(),
        "red_face_width_between_pixel_centers_m": float(measured_width),
        "off_axis_pixel_uv": [190, 120],
        "off_axis_xyz_m": edge.tolist(),
        "off_axis_range_m": float(np.linalg.norm(edge)),
        "checks": "PASS",
    }
    (OUT / "checks.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # Downsample only the viewer. Saved PLY/NPY contain every valid pixel.
    sample = np.column_stack((organized[::3, ::3].reshape(-1, 3),
                              rgb[::3, ::3].reshape(-1, 3))).round(4).tolist()
    template = Path(__file__).with_name("viewer_template.html").read_text(encoding="utf-8")
    html = template.replace("__POINTS__", json.dumps(sample))
    html = html.replace("__RGB__", png_uri(rgb)).replace("__DEPTH__", png_uri(preview))
    (OUT / "viewer.html").write_text(html, encoding="utf-8")
    print("PASS: synthetic RGB-D -> colored point cloud")
    print(f"Points: {len(points):,}")
    print(f"Pixel (160,120) -> XYZ (meters): {center.tolist()}")
    print(f"Red face width: {measured_width:.3f} m; wall depth: 2.000 m")
    print(f"Open: {OUT / 'viewer.html'}")


if __name__ == "__main__":
    main()
