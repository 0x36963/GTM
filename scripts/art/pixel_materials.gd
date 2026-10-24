class_name PixelMaterials
extends RefCounted
## Materials that draw pixel art with shaders/pixel_art.gdshader.

const SHADER := preload("res://shaders/pixel_art.gdshader")


## Uses the mesh's own UVs (sprites, facades, roofs, track strips).
static func mesh_uv(tex: Texture2D) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	mat.set_shader_parameter("albedo_tex", tex)
	return mat


## Tiles the texture across the ground in world space at tile_m metres.
static func world(tex: Texture2D, tile_m: Vector2) -> ShaderMaterial:
	var mat := mesh_uv(tex)
	mat.set_shader_parameter("world_uv", true)
	mat.set_shader_parameter("world_tile_m", tile_m)
	return mat
