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
        img = Image.fromarray(house)
        width_m = img.size[0] / px_per_m_src
        path = OUT / spec["out_dir"] / f"{name}.png"
        size = save_scaled(img, path, round(width_m * ppm), axis="w")
        out[name] = {
            "file": str(path.relative_to(OUT)),
            "size_px": size,
            "size_m": [round(size[0] / ppm, 3), round(size[1] / ppm, 3)],
        }
    return out


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    ppm = manifest["pixels_per_meter"]
    result = {"pixels_per_meter": ppm, "textures": {}, "sprites": {}, "facades": {}}
    for spec in manifest["textures"]:
        result["textures"][spec["name"]] = process_texture(spec)
        print("texture ", spec["name"])
    for spec in manifest["sprite_sheets"]:
        for name, info in process_sheet(spec, ppm).items():
            result["sprites"][name] = info
            print("sprite  ", name, info["size_px"])
    for spec in manifest["facade_rows"]:
        for name, info in process_facades(spec, ppm).items():
            result["facades"][name] = info
            print("facade  ", name, info["size_px"])
    (OUT / "art_manifest.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
