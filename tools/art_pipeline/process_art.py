"""Turn raw AI pixel art in art/raw/ into game-ready files in assets/.

Usage:  .venv/bin/python tools/art_pipeline/process_art.py

AI "pixel art" is drawn as big blocks (e.g. 5.73 source pixels per art
pixel). Every entry first recovers the art at its true resolution by finding
that block grid and sampling one value per block, then:
  textures       seamless wrap -> palette
  sprite_sheets  background removal, split into sprites, rotate, palette, recolour variants
  facade_rows    background removal, split a row of houses at shared walls, palette
Everything is driven by manifest.json next to this script. Writes
assets/art_manifest.json with each asset's real-world size for Godot.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "art" / "raw"
OUT = ROOT / "assets"
MANIFEST = Path(__file__).with_name("manifest.json")


# --- recovering the pixel grid ---------------------------------------------

def grid_phase(gray: np.ndarray, block: float, axis: int) -> float:
    """Offset of the block grid along one axis, from the edge positions."""
    edges = np.abs(np.diff(gray, axis=axis)).mean(axis=1 - axis)
    x = np.arange(len(edges)) + 0.5
    phase = np.angle((edges * np.exp(2j * np.pi * x / block)).sum())
    return (-phase / (2 * np.pi) * block) % block


def to_native(rgb: np.ndarray, block: float) -> np.ndarray:
    """Sample the median colour at the centre of every block."""
    gray = rgb.astype(np.float32).mean(axis=2)
    r = max(1, int(block / 4))
    out_axes = []
    for axis, n in ((1, rgb.shape[1]), (0, rgb.shape[0])):
        start = grid_phase(gray, block, axis) + block / 2
        if start - block / 2 > block / 2:
            start -= block
        centers = np.arange(start, n - r, block)
        out_axes.append(np.round(centers[centers >= r]).astype(int))
    xs, ys = out_axes
    out = np.zeros((len(ys), len(xs), 3), np.uint8)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            out[j, i] = np.median(rgb[y - r:y + r + 1, x - r:x + r + 1].reshape(-1, 3), axis=0)
    return out


def load_native(spec: dict) -> np.ndarray:
    img = Image.open(RAW / spec["source"]).convert("RGB")
    if "crop" in spec:
        img = img.crop(tuple(spec["crop"]))
    native = to_native(np.asarray(img), spec["pixel"]["block"])
    for r0, r1 in reversed(spec["pixel"].get("remove_rows", [])):
        native = np.concatenate([native[:r0], native[r1:]])
    return native


# --- shared steps ------------------------------------------------------------

def quantize(rgba: np.ndarray, colors: int) -> np.ndarray:
    """Reduce opaque pixels to a small palette; alpha stays binary."""
    rgb = Image.fromarray(rgba[..., :3])
    q = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = rgba.copy()
    out[..., :3] = np.asarray(q.convert("RGB"))
    out[out[..., 3] == 0] = 0
    return out


def remove_background(rgb: np.ndarray) -> np.ndarray:
    """RGBA with hard edges: near-white connected to the border is cleared."""
    near_white = (255 - rgb.astype(int)).max(axis=2) <= 40
    labels, _ = ndimage.label(near_white)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    bg = np.isin(labels, border[border > 0])
    rgba = np.dstack([rgb, np.where(bg, 0, 255).astype(np.uint8)])
    rgba[bg] = 0
    return rgba


def clear_thin_lines(rgba: np.ndarray) -> None:
    """Clear 1-pixel-thin scraps, such as leftover graph-paper grid lines."""
    thick = ndimage.binary_opening(rgba[..., 3] > 0, structure=np.ones((2, 2)))
    rgba[~thick] = 0


def keep_largest_part(rgba: np.ndarray) -> np.ndarray:
    """Clear stray specks: keep only the biggest connected opaque region."""
    labels, n = ndimage.label(rgba[..., 3] > 128)
    if n <= 1:
        return rgba
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
    out = rgba.copy()
    out[labels != int(np.argmax(sizes)) + 1] = 0
    return out


def save_png(pixels: np.ndarray, rel: str) -> Path:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(path, optimize=True)
    return path


# --- textures ----------------------------------------------------------------

def find_period(img: np.ndarray, strip: int = 24) -> int:
    """Find the length (along axis 0) at which the pattern repeats best.

    Compares the first `strip` rows against the rows at every candidate
    length in the second half of the image and returns the closest match.
    """
    n = img.shape[0]
    strip = min(strip, n // 4)
    head = img[:strip]
    best, best_len = None, n - strip
    for length in range(n // 2, n - strip):
        diff = np.abs(img[length:length + strip] - head).mean()
        if best is None or diff < best:
            best, best_len = diff, length
    return best_len


def wrap_axis(img: np.ndarray, blend: int, axis: int) -> np.ndarray:
    """Make an image tile along one axis.

    Cuts at the pattern's natural repeat length, then cross-fades a short
    band to hide what mismatch is left.
    """
    img = np.moveaxis(img, axis, 0)
    n = find_period(img)
    blend = min(blend, img.shape[0] - n)
    out = img[:n].copy()
    if blend > 0:
        w = np.linspace(0.0, 1.0, blend)[:, None, None]
        out[:blend] = img[n:n + blend] * (1 - w) + img[:blend] * w
    return np.moveaxis(out, 0, axis)


def process_texture(spec: dict) -> dict:
    native = load_native(spec).astype(np.float32)
    # A few pixels of cross-fade hide what the repeat cut leaves; quantizing
    # afterwards snaps the blended pixels back onto the palette.
    blend = spec.get("blend_px", 4)
    if "x" in spec.get("seamless", ""):
        native = wrap_axis(native, blend, axis=1)
    if "y" in spec.get("seamless", ""):
        native = wrap_axis(native, blend, axis=0)
    rgba = np.dstack([native.astype(np.uint8), np.full(native.shape[:2], 255, np.uint8)])
    rgba = quantize(rgba, spec["pixel"].get("colors", 24))
    path = save_png(rgba[..., :3], f"textures/{spec['name']}.png")
    h, w = rgba.shape[:2]
    ppm = spec["pixel"]["ppm"]
    return {"file": str(path.relative_to(OUT)), "size_px": [w, h],
            "meters": [round(w / ppm, 3), round(h / ppm, 3)]}


# --- sprite sheets -----------------------------------------------------------

def recolor(rgba: np.ndarray, hue_deg: float) -> np.ndarray:
    """Move strongly saturated reds (e.g. a hoodie) to another hue."""
    hsv = np.asarray(Image.fromarray(rgba[..., :3]).convert("HSV")).copy()
    h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    red = ((h < 12) | (h > 243)) & (s > 150) & (rgba[..., 3] > 0)
    hsv[..., 0][red] = int(hue_deg / 360 * 255) % 256
    out = rgba.copy()
    channels = [Image.fromarray(np.ascontiguousarray(hsv[..., i])) for i in range(3)]
    out[..., :3] = np.asarray(Image.merge("HSV", channels).convert("RGB"))
    return out


def process_sheet(spec: dict) -> dict:
    rgba = remove_background(load_native(spec))
    if spec["pixel"].get("open"):
        clear_thin_lines(rgba)
    solid = rgba[..., 3] > 0
    # Parts closer than merge_px (e.g. a bike's pedals) count as one sprite.
    merge = spec["pixel"].get("merge_px", 2)
    labels, n = ndimage.label(ndimage.binary_dilation(solid, iterations=merge) if merge else solid)
    boxes = [b for b, s in zip(ndimage.find_objects(labels), ndimage.sum(solid, labels, range(1, n + 1)))
             if s > 20]
    boxes.sort(key=lambda b: b[1].start)
    if len(boxes) != len(spec["sprites"]):
        raise SystemExit(f"{spec['source']}: found {len(boxes)} sprites, manifest lists {len(spec['sprites'])}")
    out = {}
    for box, sprite in zip(boxes, spec["sprites"]):
        if sprite.get("skip"):
            continue
        # Sprites face up (forward = top of the image). "rotate" is
        # counter-clockwise degrees, in quarter turns so no pixel is resampled.
        img = np.rot90(rgba[box], k=sprite.get("rotate", 0) // 90)
        img = quantize(np.ascontiguousarray(img), spec["pixel"].get("colors", 24))
        h, w = img.shape[:2]
        m_per_px = sprite["length_m"] / h
        for suffix, hue in sprite.get("variants", {"": None}).items():
            name = sprite["name"] + (f"_{suffix}" if suffix else "")
            path = save_png(img if hue is None else recolor(img, hue), f"{spec['out_dir']}/{name}.png")
            out[name] = {"file": str(path.relative_to(OUT)), "size_px": [w, h],
                         "size_m": [round(w * m_per_px, 3), round(h * m_per_px, 3)]}
    return out


# --- facades -----------------------------------------------------------------

def snap_to_wall(rgb: np.ndarray, x: int, search: int) -> int:
    """Move a rough split position onto the darkest vertical line nearby."""
    lower = rgb[rgb.shape[0] // 3:, :, :].mean(axis=2)
    lo, hi = max(0, x - search), min(rgb.shape[1], x + search)
    darkness = (lower[:, lo:hi] < 70).sum(axis=0)
    return lo + int(darkness.argmax())


def trim_edge_slivers(rgba: np.ndarray, k: int) -> np.ndarray:
    """Clear the outer k columns wherever the column just inside is empty.

    A cut along a shared wall keeps the neighbour's outline, which sticks up
    past a lower gable as a thin line.
    """
    out = rgba.copy()
    for edge, inner in ((slice(0, k), k), (slice(-k, None), -k - 1)):
        empty = out[:, inner, 3] == 0
        out[empty, edge] = 0
    return out


def process_facades(spec: dict) -> dict:
    native = load_native(spec)
    rgba = remove_background(native)
    clear_thin_lines(rgba)
    solid_cols = np.where(rgba[..., 3].max(axis=0) > 0)[0]
    left, right = int(solid_cols[0]), int(solid_cols[-1]) + 1
    cuts = [left] + [snap_to_wall(native, x, search=4) for x in spec["split_x"]] + [right]
    ppm = spec["pixel"]["ppm"]
    out = {}
    for name, x0, x1 in zip(spec["houses"], cuts, cuts[1:]):
        house = keep_largest_part(trim_edge_slivers(rgba[:, x0:x1 + 1], k=1))
        rows = np.where(house[..., 3].max(axis=1) > 0)[0]
        house = house[rows[0]:rows[-1] + 1]
        # Wall width comes from the ground floor; step gables can overhang it.
        # Eaves: scanning up from the bottom, where the wall first narrows.
        counts = (house[..., 3] > 0).sum(axis=1)
        wall_px = int(np.median(counts[-len(counts) // 3:]))
        narrow = np.where(counts[::-1] < 0.9 * wall_px)[0]
        eaves_row = len(counts) - int(narrow[0]) if len(narrow) else 0
        house = quantize(np.ascontiguousarray(house), spec["pixel"].get("colors", 32))
        path = save_png(house, f"{spec['out_dir']}/{name}.png")
        h, w = house.shape[:2]
        out[name] = {"file": str(path.relative_to(OUT)), "size_px": [w, h],
                     "size_m": [round(w / ppm, 3), round(h / ppm, 3)],
                     "wall_m": round(wall_px / ppm, 3),
                     "eaves_m": round((h - eaves_row) / ppm, 3)}
    return out


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    result = {"textures": {}, "sprites": {}, "facades": {}}
    for spec in manifest["textures"]:
        result["textures"][spec["name"]] = info = process_texture(spec)
        print("texture ", spec["name"], info["size_px"])
    for spec in manifest["sprite_sheets"]:
        for name, info in process_sheet(spec).items():
            result["sprites"][name] = info
            print("sprite  ", name, info["size_px"])
    for spec in manifest["facade_rows"]:
        for name, info in process_facades(spec).items():
            result["facades"][name] = info
            print("facade  ", name, info["size_px"], "eaves", info["eaves_m"])
    (OUT / "art_manifest.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
