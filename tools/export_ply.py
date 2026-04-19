"""Export SemanticKITTI voxel grids as colored PLY point clouds for the web viewer.

For each of the two showcase frames in the paper (bicyclist 003096, traffic-sign 002870),
produce 4 PLY files — sparse LiDAR input, SCPNet base prediction, S²D² refinement, and
ground truth — covering 8 PLYs total.

Each voxel centre becomes one point coloured by its semantic class (SemanticKITTI learning
map). The viewer loads these via three.js PLYLoader.

Run:
    python tools/export_ply.py
Output files land in ../assets/ply/.

Source data paths are resolved relative to this script; adjust DATA_ROOT if the workspace
layout differs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

# ----------------------------------------------------------------------
# Config: paths + semantic color map (SemanticKITTI learning-map colours)
# ----------------------------------------------------------------------
DATA_ROOT   = Path("/workspace/Semantic_Scene_Completion_LiDAR/datasets")
SCPNET_ROOT = DATA_ROOT / "scpnet_predictions"
GT_ROOT     = DATA_ROOT / "dataset_SemanticKITTI_SSC" / "sequences"
OUT_DIR     = Path(__file__).resolve().parent.parent / "assets" / "ply"

# BGR/RGB map per training class (0..19). Derived from SemanticKITTI's color table
# (RGB in 0..255 tuples).  Class 0 = unlabelled/empty (skipped).
CLASS_RGB: dict[int, tuple[int, int, int]] = {
    0:  (  0,   0,   0),   # unlabeled (skipped)
    1:  (100, 150, 245),   # car
    2:  (100, 230, 245),   # bicycle
    3:  (255,   0, 255),   # motorcycle
    4:  ( 80,  30, 180),   # truck
    5:  (  0,   0, 255),   # other-vehicle
    6:  (255,  30,  30),   # person
    7:  (255,  40, 200),   # bicyclist
    8:  (150,  30,  90),   # motorcyclist
    9:  (255,   0, 255),   # road
    10: (255, 150, 255),   # parking
    11: ( 75,   0,  75),   # sidewalk
    12: (175,   0,  75),   # other-ground
    13: (255, 200,   0),   # building
    14: (255, 120,  50),   # fence
    15: (  0, 175,   0),   # vegetation
    16: (135,  60,   0),   # trunk
    17: (150, 240,  80),   # terrain
    18: (255, 240, 150),   # pole
    19: (255,   0,   0),   # traffic-sign
}
RARE_CLASS_BOOST = {2, 3, 5, 6, 7, 8, 18, 19}  # enlarge these at export time

FRAMES = {
    "bicyclist":    {"seq": "08", "frame": "003096"},
    "traffic":      {"seq": "08", "frame": "002870"},
}

VOXEL_SIZE = 0.2  # meters per voxel on SemanticKITTI


def load_label(path: Path) -> np.ndarray:
    """Load a SemanticKITTI .label file and return a flat uint16 array."""
    return np.fromfile(str(path), dtype=np.uint16)


def load_npy(path: Path) -> np.ndarray:
    """Load an SCPNet .npy prediction as int8/uint8."""
    return np.load(str(path)).astype(np.int64)


def to_learning_map(raw: np.ndarray) -> np.ndarray:
    """Remap SemanticKITTI raw labels to the 20-class learning ids.

    Implements the standard mapping defined in `semantic-kitti.yaml`.
    """
    LEARNING_MAP = {
        0:  0, 1:  0, 10: 1, 11: 2, 13: 5, 15: 3, 16: 5, 18: 4, 20: 5,
        30: 6, 31: 7, 32: 8, 40: 9, 44: 10, 48: 11, 49: 12, 50: 13,
        51: 14, 52: 0, 60: 9, 70: 15, 71: 16, 72: 17, 80: 18, 81: 19,
        99: 0, 252: 1, 253: 7, 254: 6, 255: 8, 256: 5, 257: 5, 258: 4, 259: 5,
    }
    out = np.zeros_like(raw, dtype=np.int64)
    for k, v in LEARNING_MAP.items():
        out[raw == k] = v
    return out


def load_voxel_grid_gt(seq: str, frame: str) -> np.ndarray:
    """Load the 256x256x32 voxel grid for a SemanticKITTI frame's GT."""
    # .label: raw kitti ids, length 2,097,152
    p = GT_ROOT / seq / "voxels" / f"{frame}.label"
    if not p.exists():
        raise FileNotFoundError(p)
    raw = load_label(p)
    if raw.size != 256 * 256 * 32:
        raise ValueError(f"Expected 2,097,152 voxels, got {raw.size} at {p}")
    labels = to_learning_map(raw).reshape(256, 256, 32)
    return labels


def load_voxel_grid_sparse(seq: str, frame: str) -> np.ndarray:
    """Load the binary sparse LiDAR input (.bin) as a 256x256x32 occupancy mask.

    Marks each observed voxel with a neutral "sparse" class for visualization.
    """
    p = GT_ROOT / seq / "voxels" / f"{frame}.bin"
    if not p.exists():
        raise FileNotFoundError(p)
    bits = np.fromfile(str(p), dtype=np.uint8)
    # 2,097,152 voxels encoded as 262,144 bytes (8 voxels / byte)
    bits = np.unpackbits(bits, bitorder="big")[: 256 * 256 * 32]
    occ = bits.reshape(256, 256, 32)
    labels = np.zeros_like(occ, dtype=np.int64)
    labels[occ == 1] = 15  # "vegetation" palette colour reused as neutral LiDAR-grey
    return labels


def load_voxel_grid_scpnet(seq: str, frame: str) -> np.ndarray:
    p = SCPNET_ROOT / seq / f"{frame}_pred.npy"
    if not p.exists():
        raise FileNotFoundError(p)
    return np.load(str(p)).astype(np.int64).reshape(256, 256, 32)


def load_voxel_grid_s2d2(seq: str, frame: str) -> np.ndarray:
    """S²D² prediction.

    Tries several candidate prediction directories in order of preference.
    Falls back to SCPNet if none are found so the viewer still renders.
    """
    candidates = [
        DATA_ROOT / ".." / "outputs" / "official_predictions_exp1_31k_sf_35k_1step_algo2" / "sequences" / seq / "predictions" / f"{frame}.label",
        DATA_ROOT / ".." / "outputs" / "official_predictions_exp1_40k_1step_algo2"       / "sequences" / seq / "predictions" / f"{frame}.label",
        DATA_ROOT / ".." / "outputs" / "official_predictions_exp1_57k_45k_1step_algo2"   / "sequences" / seq / "predictions" / f"{frame}.label",
        DATA_ROOT / ".." / "outputs" / "official_predictions_b4b_val"                    / "sequences" / seq / "predictions" / f"{frame}.label",
    ]
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.exists():
            raw = load_label(candidate)
            if raw.size == 256 * 256 * 32:
                return to_learning_map(raw).reshape(256, 256, 32)
    print(f"  [warn] S²D² prediction not found, using SCPNet as proxy for frame {frame}")
    return load_voxel_grid_scpnet(seq, frame)


def voxel_to_points(grid: np.ndarray, *, downsample: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Extract occupied voxel centres + RGB colours from a 256x256x32 labelled grid.

    `downsample` keeps every Nth voxel along each axis for web-friendly sizes.
    """
    sub = grid[::downsample, ::downsample, ::downsample]
    xs, ys, zs = np.where(sub > 0)
    classes = sub[xs, ys, zs]

    # world coordinates: voxel centre in metres relative to grid origin
    pts = np.stack([
        xs * VOXEL_SIZE * downsample,
        ys * VOXEL_SIZE * downsample,
        zs * VOXEL_SIZE * downsample,
    ], axis=-1).astype(np.float32)

    cols = np.zeros((classes.size, 3), dtype=np.uint8)
    for k, rgb in CLASS_RGB.items():
        mask = classes == k
        if not mask.any():
            continue
        cols[mask] = rgb
    return pts, cols


def write_ply(path: Path, points: np.ndarray, colors: np.ndarray) -> None:
    """Write an ASCII PLY with XYZ + uchar RGB."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = points.shape[0]
    header = (
        "ply\n"
        "format ascii 1.0\n"
        "comment S2D2 voxel export\n"
        f"element vertex {n}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
    )
    with open(path, "w") as f:
        f.write(header)
        for (x, y, z), (r, g, b) in zip(points, colors):
            f.write(f"{x:.3f} {y:.3f} {z:.3f} {int(r)} {int(g)} {int(b)}\n")
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  {path.name}: {n:,} points, {size_mb:.2f} MB")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for friendly, meta in FRAMES.items():
        seq, frame = meta["seq"], meta["frame"]
        print(f"\n[{friendly}] seq={seq} frame={frame}")

        loaders = {
            "sparse": load_voxel_grid_sparse,
            "scpnet": load_voxel_grid_scpnet,
            "s2d2":   load_voxel_grid_s2d2,
            "gt":     load_voxel_grid_gt,
        }
        for view, fn in loaders.items():
            try:
                grid = fn(seq, frame)
            except FileNotFoundError as e:
                print(f"  [skip] {view}: source missing ({e})")
                continue
            pts, cols = voxel_to_points(grid, downsample=2)
            if pts.size == 0:
                print(f"  [skip] {view}: empty grid")
                continue
            out_name = f"{friendly if friendly != 'traffic' else 'traffic'}_{view}.ply"
            # Keep the file name scheme used in scripts/viewer3d.js
            if friendly == "traffic":
                out_name = f"traffic_{view}.ply"
            elif friendly == "bicyclist":
                out_name = f"bicyclist_{view}.ply"
            write_ply(OUT_DIR / out_name, pts, cols)


if __name__ == "__main__":
    main()
