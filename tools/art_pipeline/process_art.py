"""Turn raw AI generations in art/raw/ into game-ready files in assets/.

Usage:  .venv/bin/python tools/art_pipeline/process_art.py

Everything is driven by manifest.json next to this script:
  textures       crop -> optional contrast reduction -> seamless wrap -> resize
  sprite_sheets  white background -> alpha, split into separate sprites, scale to real size
  facade_rows    white background -> alpha, split a row of houses at shared walls
Writes assets/art_manifest.json with real-world sizes for the Godot importer.
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

# Pixels this close to pure white (per channel) count as background.
BG_TOLERANCE = 28
# Width of the anti-aliased edge band that gets un-blended from white.
FRINGE_PX = 3


# --- pixel art --------------------------------------------------------------
#
# AI "pixel art" is drawn as big blocks (e.g. 5.73 source pixels per art
# pixel). to_native() finds that grid and samples one value per block, which
# recovers the art at its true resolution. Entries opt in with "pixel": {...}.

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


def quantize(rgba: np.ndarray, colors: int) -> np.ndarray:
    """Reduce opaque pixels to a small palette; alpha stays binary."""
    rgb = Image.fromarray(rgba[..., :3])
    q = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = rgba.copy()
    out[..., :3] = np.asarray(q.convert("RGB"))
    out[out[..., 3] == 0] = 0
    return out


def binary_background(rgb: np.ndarray) -> np.ndarray:
    """RGBA with hard edges: near-white connected to the border is cleared."""
    near_white = (255 - rgb.astype(int)).max(axis=2) <= 40
    labels, _ = ndimage.label(near_white)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    bg = np.isin(labels, border[border > 0])
    rgba = np.dstack([rgb, np.where(bg, 0, 255).astype(np.uint8)])
    rgba[bg] = 0
    return rgba


def load_native(spec: dict) -> np.ndarray:
    img = Image.open(RAW / spec["source"]).convert("RGB")
    if "crop" in spec:
        img = img.crop(tuple(spec["crop"]))
    native = to_native(np.asarray(img), spec["pixel"]["block"])
    for r0, r1 in reversed(spec["pixel"].get("remove_rows", [])):
        native = np.concatenate([native[:r0], native[r1:]])
    return native


def save_png(rgba_or_rgb: np.ndarray, rel: str) -> Path:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba_or_rgb).save(path, optimize=True)
    return path


def process_pixel_texture(spec: dict) -> dict:
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
            "meters": [round(w / ppm, 3), round(h / ppm, 3)], "pixel": True}


def process_pixel_sheet(spec: dict) -> dict:
    rgba = binary_background(load_native(spec))
    solid = rgba[..., 3] > 0
    labels, n = ndimage.label(ndimage.binary_dilation(solid, iterations=2))
    boxes = [b for b, s in zip(ndimage.find_objects(labels), ndimage.sum(solid, labels, range(1, n + 1)))
             if s > 20]
    boxes.sort(key=lambda b: b[1].start)
    if len(boxes) != len(spec["sprites"]):
        raise SystemExit(f"{spec['source']}: found {len(boxes)} sprites, manifest lists {len(spec['sprites'])}")
    out = {}
    for box, sprite in zip(boxes, spec["sprites"]):
        if sprite.get("skip"):
            continue
        img = rgba[box]
        # Pixel art turns in exact quarter steps so no pixel gets resampled.
        # "rotate" is counter-clockwise degrees, as in the line-art path.
        img = np.rot90(img, k=sprite.get("rotate", 0) // 90)
        img = quantize(np.ascontiguousarray(img), spec["pixel"].get("colors", 24))
        path = save_png(img, f"{spec['out_dir']}/{sprite['name']}.png")
        h, w = img.shape[:2]
        m_per_px = sprite["length_m"] / h
        out[sprite["name"]] = {"file": str(path.relative_to(OUT)), "size_px": [w, h],
                               "size_m": [round(w * m_per_px, 3), round(h * m_per_px, 3)], "pixel": True}
    return out


def process_pixel_facades(spec: dict) -> dict:
    native = load_native(spec)
    rgba = binary_background(native)
    # Clear 1-pixel-thin scraps (leftover background grid lines) from edges.
    thick = ndimage.binary_opening(rgba[..., 3] > 0, structure=np.ones((2, 2)))
    rgba[~thick] = 0
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
                     "eaves_m": round((h - eaves_row) / ppm, 3), "pixel": True}
    return out


# --- textures -------------------------------------------------------------

def reduce_contrast(rgb: np.ndarray, amount: float) -> np.ndarray:
    """Pull every pixel toward the image mean. amount=1 keeps it, 0 flattens it."""
    mean = rgb.reshape(-1, 3).mean(axis=0)
    return mean + (rgb - mean) * amount


def find_period(img: np.ndarray, strip: int = 24) -> int:
    """Find the length (along axis 0) at which the pattern repeats best.

    Compares the first `strip` rows against the rows at every candidate
    length in the second half of the image and returns the closest match.
    """
    n = img.shape[0]
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
    src = Image.open(RAW / spec["source"]).convert("RGB").crop(tuple(spec["crop"]))
    rgb = np.asarray(src).astype(np.float32)
    if "contrast" in spec:
        rgb = reduce_contrast(rgb, spec["contrast"])
    blend = spec.get("blend_px", 96)
    if "x" in spec.get("seamless", ""):
        rgb = wrap_axis(rgb, blend, axis=1)
    if "y" in spec.get("seamless", ""):
        rgb = wrap_axis(rgb, blend, axis=0)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    # The seamless cut changes the aspect ratio, so only the width is fixed.
    w = spec["out_width"]
    h = round(img.height * w / img.width)
    img = img.resize((w, h), Image.LANCZOS)
    path = OUT / "textures" / f"{spec['name']}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    width_m = spec["width_m"]
    return {"file": str(path.relative_to(OUT)), "size_px": [w, h],
            "meters": [width_m, round(width_m * h / w, 3)]}


# --- background removal ---------------------------------------------------

def remove_white_background(rgb: np.ndarray, fill_holes: bool) -> np.ndarray:
    """Return RGBA where white connected to the image border becomes transparent.

    Enclosed white areas (e.g. the white body of a tram) are kept unless
    fill_holes is set, in which case enclosed near-pure-white pockets go too.
    """
    near_white = (255 - rgb).max(axis=2) <= BG_TOLERANCE
    labels, _ = ndimage.label(near_white)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    bg = np.isin(labels, border[border > 0])
    if fill_holes:
        bg |= (255 - rgb).max(axis=2) <= 8

    # Un-blend the anti-aliased fringe from white so edges don't glow.
    fringe = ndimage.binary_dilation(bg, iterations=FRINGE_PX) & ~bg
    alpha = np.where(bg, 0.0, 1.0)
    rgbf = rgb.astype(np.float32)
    a_fringe = ((255.0 - rgbf).max(axis=2) / 255.0).clip(0.05, 1.0)
    alpha[fringe] = a_fringe[fringe]
    unblended = (rgbf - 255.0 * (1 - a_fringe[..., None])) / a_fringe[..., None]
    rgbf[fringe] = unblended[fringe]

    rgba = np.dstack([rgbf.clip(0, 255), alpha * 255]).astype(np.uint8)
    rgba[bg] = 0
    return rgba


def keep_largest_part(rgba: np.ndarray) -> np.ndarray:
    """Clear stray specks: keep only the biggest connected opaque region."""
    # Label on mostly-opaque pixels so faint edge pixels can't bridge a speck.
    labels, n = ndimage.label(rgba[..., 3] > 128)
    if n <= 1:
        return rgba
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
    out = rgba.copy()
    out[labels != int(np.argmax(sizes)) + 1] = 0
    return out


def trim_edge_slivers(rgba: np.ndarray, k: int = 6) -> np.ndarray:
    """Clear the outer k columns wherever the column just inside is empty.

    A cut along a shared wall keeps the neighbour's outline, which sticks up
    past a lower gable as a thin line.
    """
    out = rgba.copy()
    for edge, inner in ((slice(0, k), k), (slice(-k, None), -k - 1)):
        empty = out[:, inner, 3] == 0
        out[empty, edge] = 0
    return out


def resize_rgba(img: Image.Image, size: tuple) -> Image.Image:
    # Premultiply so transparent pixels don't bleed dark or white into edges.
    return img.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")


def save_scaled(img: Image.Image, path: Path, length_px: int, axis: str) -> tuple:
    w, h = img.size
    s = length_px / (h if axis == "h" else w)
    size = (max(1, round(w * s)), max(1, round(h * s)))
    path.parent.mkdir(parents=True, exist_ok=True)
    resize_rgba(img, size).save(path, optimize=True)
    return size


# --- sprite sheets --------------------------------------------------------

def split_sprites(rgba: np.ndarray, expected: int) -> list:
    """Find separate objects on a transparent sheet, sorted left to right."""
    solid = rgba[..., 3] > 0
    # Merge parts that nearly touch (oars, handlebar ends) into one object.
    merged = ndimage.binary_dilation(solid, iterations=12)
    labels, n = ndimage.label(merged)
    boxes = ndimage.find_objects(labels)
    sizes = ndimage.sum(solid, labels, range(1, n + 1))
    keep = [b for b, s in zip(boxes, sizes) if s > 2000]
    keep.sort(key=lambda b: b[1].start)
    if len(keep) != expected:
        raise SystemExit(f"found {len(keep)} sprites, manifest lists {expected}")
    return keep


def process_sheet(spec: dict, ppm: int) -> dict:
    rgb = np.asarray(Image.open(RAW / spec["source"]).convert("RGB"))
    rgba = remove_white_background(rgb, spec.get("fill_holes", False))
    out = {}
    for box, sprite in zip(split_sprites(rgba, len(spec["sprites"])), spec["sprites"]):
        if sprite.get("skip"):
            continue
        img = Image.fromarray(rgba[box])
        # Normalise every sprite to face up (forward = -Y in the image).
        if sprite.get("rotate"):
            img = img.rotate(sprite["rotate"], expand=True)
        path = OUT / spec["out_dir"] / f"{sprite['name']}.png"
        size = save_scaled(img, path, round(sprite["length_m"] * ppm), axis="h")
        out[sprite["name"]] = {
            "file": str(path.relative_to(OUT)),
            "size_px": size,
            "size_m": [round(size[0] / ppm, 3), round(size[1] / ppm, 3)],
        }
    return out


# --- facades --------------------------------------------------------------

def snap_to_wall(rgb: np.ndarray, x: int, search: int = 30) -> int:
    """Move a rough split position onto the darkest vertical line nearby."""
    lower = rgb[rgb.shape[0] // 3:, :, :].mean(axis=2)
    lo, hi = max(0, x - search), min(rgb.shape[1], x + search)
    darkness = (lower[:, lo:hi] < 70).sum(axis=0)
    return lo + int(darkness.argmax())


def process_facades(spec: dict, ppm: int) -> dict:
    rgb = np.asarray(Image.open(RAW / spec["source"]).convert("RGB"))
    rgba = remove_white_background(rgb, fill_holes=False)
    solid_cols = np.where(rgba[..., 3].max(axis=0) > 0)[0]
    left, right = int(solid_cols[0]), int(solid_cols[-1]) + 1
    cuts = [left] + [snap_to_wall(rgb, x) for x in spec["split_x"]] + [right]
    px_per_m_src = (right - left) / spec["row_width_m"]

    out = {}
    for name, x0, x1 in zip(spec["houses"], cuts, cuts[1:]):
        house = keep_largest_part(trim_edge_slivers(rgba[:, x0:x1 + 1]))
        rows = np.where(house[..., 3].max(axis=1) > 0)[0]
        house = house[rows[0]:]
        # Eaves: the first row (from the top) where the wall spans the full
        # width. Everything above it is the decorative gable.
        coverage = (house[..., 3] > 128).mean(axis=1)
        eaves_row = int(np.argmax(coverage >= 0.9))
        img = Image.fromarray(house)
        width_m = img.size[0] / px_per_m_src
        path = OUT / spec["out_dir"] / f"{name}.png"
        size = save_scaled(img, path, round(width_m * ppm), axis="w")
        height_m = size[1] / ppm
        out[name] = {
            "file": str(path.relative_to(OUT)),
            "size_px": size,
            "size_m": [round(size[0] / ppm, 3), round(height_m, 3)],
            "eaves_m": round(height_m * (1 - eaves_row / house.shape[0]), 3),
        }
    return out


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    ppm = manifest["pixels_per_meter"]
    result = {"pixels_per_meter": ppm, "textures": {}, "sprites": {}, "facades": {}}
    for spec in manifest["textures"]:
        info = process_pixel_texture(spec) if "pixel" in spec else process_texture(spec)
        result["textures"][spec["name"]] = info
        print("texture ", spec["name"], info.get("size_px", ""))
    for spec in manifest["sprite_sheets"]:
        sheet = process_pixel_sheet(spec) if "pixel" in spec else process_sheet(spec, ppm)
        for name, info in sheet.items():
            result["sprites"][name] = info
            print("sprite  ", name, info["size_px"])
    for spec in manifest["facade_rows"]:
        rows = process_pixel_facades(spec) if "pixel" in spec else process_facades(spec, ppm)
        for name, info in rows.items():
            result["facades"][name] = info
            print("facade  ", name, info["size_px"], "eaves", info["eaves_m"])
    (OUT / "art_manifest.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
