class_name ArtDb
extends RefCounted
## Reads assets/art_manifest.json, written by tools/art_pipeline/process_art.py.
## Gives scenes each asset's texture and real-world size in metres.

const MANIFEST_PATH := "res://assets/art_manifest.json"

static var _data: Dictionary = {}


static func data() -> Dictionary:
	if _data.is_empty():
		_data = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
	return _data


static func entry(group: String, asset_name: String) -> Dictionary:
	return data()[group][asset_name]


static func texture(asset: Dictionary) -> Texture2D:
	return load("res://assets/" + str(asset["file"])) as Texture2D


## Size in metres. Sprites and facades use "size_m", textures "meters".
static func meters(asset: Dictionary, key: String = "size_m") -> Vector2:
	var m: Array = asset[key]
	return Vector2(m[0], m[1])


## Metres per texture pixel for a sprite or facade.
static func pixel_size(asset: Dictionary) -> float:
	var px: Array = asset["size_px"]
	return meters(asset).x / float(px[0])


## Pixel art is sampled with nearest filtering so its pixels stay square.
static func filter(_asset: Dictionary = {}) -> BaseMaterial3D.TextureFilter:
	return BaseMaterial3D.TEXTURE_FILTER_NEAREST_WITH_MIPMAPS
