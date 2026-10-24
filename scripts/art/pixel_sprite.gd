class_name PixelSprite
extends MeshInstance3D
## A flat top-down pixel-art sprite lying on the ground plane, sized in
## metres from assets/art_manifest.json. Forward (the top of the image) is -Z.

var flip_h := false:
	set(value):
		flip_h = value
		if _mat:
			_mat.set_shader_parameter("flip_h", value)

var _mat: ShaderMaterial


func set_asset(asset: Dictionary) -> void:
	var plane := mesh as PlaneMesh
	if plane == null:
		plane = PlaneMesh.new()
		mesh = plane
	plane.size = ArtDb.meters(asset)
	var tex := ArtDb.texture(asset)
	if _mat == null:
		_mat = PixelMaterials.mesh_uv(tex)
		material_override = _mat
	else:
		_mat.set_shader_parameter("albedo_tex", tex)
	_mat.set_shader_parameter("flip_h", flip_h)
