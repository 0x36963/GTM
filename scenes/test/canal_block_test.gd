extends Node3D
## Canal block test: a tiny Amsterdam block built from the processed art and
## seen through the GTA 2 camera. Everything is generated in code from
## assets/art_manifest.json so new art shows up without editing the scene.
##
## Pixel art is drawn at full screen resolution with shaders/pixel_art.gdshader,
## which keeps pixels crisp without shimmering as the camera moves. P switches
## to rendering the world at ~360 lines instead, for comparison.
##
## Controls: WASD/arrows drive, Z/X zoom, N night, P low-res render.
## Screenshot mode:
##   Godot --path . -- --screenshot=out.png [--pixel=4] [--height=40] [--night]
##
## Layout (metres, -Z is north/up on screen): a canal runs east-west through
## the middle, crossed by a street and a tram line. Two back-to-back rows of
## canal houses stand on each side.

const X_MIN := -70.0
const X_MAX := 60.0
const Z_EXTENT := 60.0
const CANAL_HALF := 8.0
const WATER_Y := -1.4
const ROW_DEPTH := 12.0
const SIDEWALK := 2.5
const CHUNK := 10.0
const TRAM_X := 36.0
## x ranges that cut through the house rows and quay railings.
const STREETS := [Vector2(-6.0, 6.0), Vector2(34.0, 47.0)]
## [front z, facing] per house row. Facing +1 means the facade faces +Z.
const ROWS := [[-18.0, 1.0], [-42.0, -1.0], [18.0, -1.0], [42.0, 1.0]]
## The world renders at about this many lines whatever the screen size,
## using the nearest whole-number pixel size.
const TARGET_LINES := 360
const PLAYER_COLORS := ["red", "yellow", "green", "blue", "purple"]
const PARKED_CARS := ["car_red", "car_yellow", "car_white", "car_blue"]
const WALK_SPEED := 1.4
const STEP_TIME := 0.25

var _rng := RandomNumberGenerator.new()
var _night := false
var _night_lights: Array[Light3D] = []
var _wall_colors: Dictionary = {}
var _env: Environment
var _sun: DirectionalLight3D
var _water_mat: ShaderMaterial
var _water_offset := 0.0
var _roof_mat: ShaderMaterial
var _iron_mat: StandardMaterial3D
var _lamp_head_mat: StandardMaterial3D
var _tram: PixelSprite
var _pixel_lines := 0
var _tram_dir := -1.0
var _hud: Label
var _shot_path := ""
var _frames := 0
var _keys_down: Dictionary = {}
## Placeholder players pacing along the sidewalk: [sprite, colour, start x, phase].
var _walkers: Array = []
var _walk_time := 0.0

@onready var _car: Car = $Car
@onready var _camera: GtaCamera = $GtaCamera
@onready var _view: SubViewportContainer = get_parent().get_parent()


func _ready() -> void:
	_rng.seed = 7
	_iron_mat = _color_mat(Color(0.13, 0.12, 0.17))
	_build_environment()
	_build_ground()
	_build_canal()
	_build_houses()
	_build_quays()
	_build_tram()
	_build_players()
	_build_bounds()
	_build_hud()
	_car.position = Vector3(-20.0, 0.0, -14.3)
	_car.heading = -PI / 2.0
	# Full resolution by default; P switches to the old low-res render to compare.
	var screen_h := get_tree().root.get_visible_rect().size.y
	_pixel_lines = maxi(1, roundi(screen_h / TARGET_LINES))
	_view.stretch_shrink = 1
	_parse_args()
	_set_night(_night)


func _process(delta: float) -> void:
	_water_offset += delta * 0.01
	_water_mat.set_shader_parameter("uv_offset", Vector2(_water_offset, 0.0))
	_move_tram(delta)
	_move_walkers(delta)

	var zoom_input := float(Input.is_physical_key_pressed(KEY_X)) - float(Input.is_physical_key_pressed(KEY_Z))
	_camera.base_height = clampf(_camera.base_height + zoom_input * 20.0 * delta, 15.0, 90.0)
	if _just_pressed(KEY_N):
		_set_night(not _night)
	if _just_pressed(KEY_P):
		_view.stretch_shrink = _pixel_lines if _view.stretch_shrink == 1 else 1
	_hud.text = "WASD / arrows: drive    Z/X: height %d m    N: %s    P: %s" % [
		roundi(_camera.base_height), "day" if _night else "night",
		"full resolution" if _view.stretch_shrink > 1 else "low-res render"]

	if _shot_path != "":
		_frames += 1
		if _frames == 60:
			_take_screenshot()


## Polled instead of using input events, which the SubViewportContainer
## doesn't forward for keys.
func _just_pressed(key: Key) -> bool:
	var down := Input.is_physical_key_pressed(key)
	var was_down: bool = _keys_down.get(key, false)
	_keys_down[key] = down
	return down and not was_down


# --- setup ----------------------------------------------------------------

func _parse_args() -> void:
	for arg in OS.get_cmdline_user_args():
		var parts := arg.trim_prefix("--").split("=")
		match parts[0]:
			"screenshot":
				_shot_path = parts[1]
			"pixel":
				_view.stretch_shrink = int(parts[1])
			"height":
				_camera.base_height = float(parts[1])
			"night":
				_night = true


func _take_screenshot() -> void:
	await RenderingServer.frame_post_draw
	# The root viewport holds the upscaled world plus the HUD.
	get_tree().root.get_texture().get_image().save_png(_shot_path)
	get_tree().quit()


func _build_environment() -> void:
	_env = Environment.new()
	_env.background_mode = Environment.BG_COLOR
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	_env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var world_env := WorldEnvironment.new()
	world_env.environment = _env
	add_child(world_env)
	_sun = DirectionalLight3D.new()
	_sun.rotation_degrees = Vector3(-65.0, 30.0, 0.0)
	add_child(_sun)


## Day is flat, neutral light so the art shows its true colours. Night is the
## mood target: dark blue ambient, warm canal lamps and headlights.
func _set_night(on: bool) -> void:
	_night = on
	_env.background_color = Color(0.04, 0.04, 0.08) if on else Color(0.55, 0.57, 0.6)
	_env.ambient_light_color = Color(0.32, 0.36, 0.62) if on else Color.WHITE
	_env.ambient_light_energy = 0.22 if on else 0.85
	_sun.light_energy = 0.0 if on else 0.3
	_lamp_head_mat.emission_energy_multiplier = 4.0 if on else 0.0
	for light in _night_lights:
		light.visible = on
	_car.set_headlights(on)


# --- ground, canal, bridges ----------------------------------------------

func _build_ground() -> void:
	var cobble := _world_mat("cobblestone")
	_ground_rect(X_MIN, X_MAX, -Z_EXTENT, -CANAL_HALF, 0.0, cobble)
	_ground_rect(X_MIN, X_MAX, CANAL_HALF, Z_EXTENT, 0.0, cobble)

	# The track texture's rails already run north-south (along V).
	var tracks := ArtDb.entry("textures", "tram_tracks")
	var tile := ArtDb.meters(tracks, "meters")
	var mat := PixelMaterials.mesh_uv(ArtDb.texture(tracks))
	var z := -Z_EXTENT + 1.5
	while z + tile.y <= Z_EXTENT - 1.5:
		_add_plane(Vector2(tile.x, tile.y), Vector3(TRAM_X + tile.x / 2.0, 0.05, z + tile.y / 2.0), mat)
		z += tile.y


func _build_canal() -> void:
	_water_mat = _world_mat("canal_water")
	_add_plane(Vector2(X_MAX - X_MIN, CANAL_HALF * 2.0), Vector3((X_MIN + X_MAX) / 2.0, WATER_Y, 0.0), _water_mat)

	var brick := _color_mat(Color(0.33, 0.23, 0.2))
	var wall_h := -WATER_Y + 0.5
	for side: float in [-1.0, 1.0]:
		_add_box(Vector3(X_MAX - X_MIN, wall_h, 0.4),
			Vector3((X_MIN + X_MAX) / 2.0, -wall_h / 2.0, side * (CANAL_HALF - 0.2)), brick)

	var deck := _world_mat("cobblestone")
	for street: Vector2 in STREETS:
		var width := street.y - street.x
		var length := CANAL_HALF * 2.0 + 1.0
		var cx := (street.x + street.y) / 2.0
		_add_box(Vector3(width, 0.6, length), Vector3(cx, -0.27, 0.0), deck)
		for edge: float in [street.x + 0.15, street.y - 0.15]:
			_add_railing(Vector3(edge, 0.0, 0.0), length, true)


func _ground_rect(x0: float, x1: float, z0: float, z1: float, y: float, mat: Material) -> void:
	# Chunked so the mobile renderer's per-mesh light limit isn't hit at night.
	var x := x0
	while x < x1 - 0.001:
		var w := minf(CHUNK, x1 - x)
		var z := z0
		while z < z1 - 0.001:
			var d := minf(CHUNK, z1 - z)
			_add_plane(Vector2(w, d), Vector3(x + w / 2.0, y, z + d / 2.0), mat)
			z += d
		x += w


# --- houses ---------------------------------------------------------------

func _build_houses() -> void:
	var facades: Dictionary = ArtDb.data()["facades"]
	var names: Array = facades.keys()
	var sidewalk := _world_mat("sidewalk_herringbone")
	var roof_entry := ArtDb.entry("textures", "roof_tiles")
	_roof_mat = PixelMaterials.mesh_uv(ArtDb.texture(roof_entry))

	for row: Array in ROWS:
		var z_front: float = row[0]
		var facing: float = row[1]
		var walk_z := z_front + facing * SIDEWALK / 2.0
		for seg in _segments(X_MIN + 2.0, X_MAX - 2.0, 1.0):
			_ground_rect(seg.x, seg.y, walk_z - SIDEWALK / 2.0, walk_z + SIDEWALK / 2.0, 0.02, sidewalk)
			var x := seg.x
			while true:
				var facade: Dictionary = facades[names[_rng.randi() % names.size()]]
				# Houses stand wall to wall; a gable may overhang the wall.
				var w: float = facade.get("wall_m", ArtDb.meters(facade).x)
				if x + w > seg.y:
					break
				_add_house(facade, x, w, z_front, facing)
				x += w
			var center := Vector3((seg.x + x) / 2.0, 3.0, z_front - facing * ROW_DEPTH / 2.0)
			_add_static_box(Vector3(x - seg.x, 6.0, ROW_DEPTH), center)


func _add_house(facade: Dictionary, x0: float, w: float, z_front: float, facing: float) -> void:
	var tex := ArtDb.texture(facade)
	var size := ArtDb.meters(facade)
	var eaves: float = facade["eaves_m"]
	var peak := maxf(size.y - 0.4, eaves + 2.0)
	var center := Vector3(x0 + w / 2.0, 0.0, z_front - facing * ROW_DEPTH / 2.0)
	var wall := _color_mat(_wall_color(tex))

	_add_box(Vector3(w, eaves, ROW_DEPTH), center + Vector3(0.0, eaves / 2.0, 0.0), wall)

	var roof := MeshInstance3D.new()
	roof.mesh = _roof_mesh(w, ROW_DEPTH, eaves, peak, wall)
	roof.position = center
	add_child(roof)

	var quad := QuadMesh.new()
	quad.size = size
	var front := MeshInstance3D.new()
	front.mesh = quad
	front.material_override = PixelMaterials.mesh_uv(tex)
	front.position = Vector3(center.x, size.y / 2.0, z_front + facing * 0.03)
	if facing < 0.0:
		front.rotation.y = PI
	add_child(front)


## Gabled roof with the ridge running front to back, plus brick gable ends.
func _roof_mesh(w: float, depth: float, eaves: float, peak: float, end_mat: Material) -> ArrayMesh:
	var tile := ArtDb.meters(ArtDb.entry("textures", "roof_tiles"), "meters")
	var hw := w / 2.0 + 0.1
	var hd := depth / 2.0
	var rise := peak - eaves
	var slope_v := Vector2(hw, rise).length() / tile.y

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for side: float in [-1.0, 1.0]:
		var normal := Vector3(side * rise, hw, 0.0).normalized()
		var eave_f := Vector3(side * hw, eaves, -hd)
		var eave_b := Vector3(side * hw, eaves, hd)
		var ridge_f := Vector3(0.0, peak, -hd)
		var ridge_b := Vector3(0.0, peak, hd)
		var u0 := -hd / tile.x
		var u1 := hd / tile.x
		for v: Array in [[ridge_f, u0, 0.0], [eave_f, u0, slope_v], [eave_b, u1, slope_v],
				[ridge_f, u0, 0.0], [eave_b, u1, slope_v], [ridge_b, u1, 0.0]]:
			st.set_normal(normal)
			st.set_uv(Vector2(v[1], v[2]))
			st.add_vertex(v[0])
	st.set_material(_roof_mat)
	var mesh := st.commit()

	var ends := SurfaceTool.new()
	ends.begin(Mesh.PRIMITIVE_TRIANGLES)
	for z: float in [-hd, hd]:
		for p: Vector3 in [Vector3(-w / 2.0, eaves, z), Vector3(w / 2.0, eaves, z), Vector3(0.0, peak, z)]:
			ends.set_normal(Vector3(0.0, 0.0, signf(z)))
			ends.add_vertex(p)
	ends.set_material(end_mat)
	return ends.commit(mesh)


## Side and back walls use the facade's brick colour, sampled from the strip
## between the left edge and the first column of windows.
func _wall_color(tex: Texture2D) -> Color:
	if _wall_colors.has(tex):
		return _wall_colors[tex]
	var img := tex.get_image()
	if img.is_compressed():
		img.decompress()
	var w := img.get_width()
	var h := img.get_height()
	var sum := Color(0, 0, 0, 0)
	var n := 0
	for y in range(int(h * 0.45), int(h * 0.9), 4):
		for x in range(int(w * 0.03), int(w * 0.08)):
			var c := img.get_pixel(x, y)
			if c.a > 0.9:
				sum += c
				n += 1
	var color := sum / float(n) if n > 0 else Color(0.4, 0.3, 0.25)
	color.a = 1.0
	_wall_colors[tex] = color
	return color


# --- quays, props ---------------------------------------------------------

func _build_quays() -> void:
	_lamp_head_mat = _color_mat(Color(1.0, 0.88, 0.6))
	_lamp_head_mat.emission_enabled = true
	_lamp_head_mat.emission = Color(1.0, 0.7, 0.3)

	for side: float in [-1.0, 1.0]:
		for seg in _segments(X_MIN, X_MAX, 0.0):
			var length := seg.y - seg.x
			_add_railing(Vector3((seg.x + seg.y) / 2.0, 0.0, side * (CANAL_HALF + 0.3)), length, false)
			var x := seg.x + 4.0
			while x < seg.y - 2.0:
				_add_lamp(Vector3(x, 0.0, side * (CANAL_HALF + 0.9)))
				_add_bikes(x + _rng.randf_range(3.0, 9.0), side)
				x += 16.0
			x = seg.x + 3.0
			while x < seg.y - 3.0:
				if _rng.randf() < 0.45:
					_add_parked_car(Vector3(x, 0.0, side * (CANAL_HALF + 3.6)))
				x += 6.0

	var boat_x := X_MIN + 10.0
	while boat_x < X_MAX - 10.0:
		var near_bridge := false
		for street: Vector2 in STREETS:
			near_bridge = near_bridge or (boat_x > street.x - 11.0 and boat_x < street.y + 11.0)
		if not near_bridge:
			var side := -1.0 if _rng.randf() < 0.5 else 1.0
			_add_sprite("houseboat", Vector3(boat_x, WATER_Y + 0.05, side * (CANAL_HALF - 3.2)), PI / 2.0 * side)
		boat_x += _rng.randf_range(20.0, 26.0)
	_add_sprite("rowboat", Vector3(-28.0, WATER_Y + 0.05, 1.5), 0.4)
	_add_sprite("rowboat", Vector3(18.0, WATER_Y + 0.05, -2.0), -1.2)


func _add_railing(center: Vector3, length: float, along_z: bool) -> void:
	var size := Vector3(0.08, 0.12, length) if along_z else Vector3(length, 0.12, 0.08)
	_add_box(size, center + Vector3(0.0, 0.9, 0.0), _iron_mat)
	var steps := int(length / 2.5)
	for i in steps + 1:
		var t := -length / 2.0 + length * float(i) / float(maxi(steps, 1))
		var offset := Vector3(0.0, 0.45, t) if along_z else Vector3(t, 0.45, 0.0)
		_add_box(Vector3(0.08, 0.9, 0.08), center + offset, _iron_mat)
	var shape := Vector3(0.3, 2.0, length) if along_z else Vector3(length, 2.0, 0.3)
	_add_static_box(shape, center + Vector3(0.0, 1.0, 0.0))


func _add_lamp(base: Vector3) -> void:
	var post := CylinderMesh.new()
	post.top_radius = 0.07
	post.bottom_radius = 0.09
	post.height = 4.2
	_add_mesh(post, base + Vector3(0.0, 2.1, 0.0), _iron_mat)
	var head := SphereMesh.new()
	head.radius = 0.28
	head.height = 0.56
	_add_mesh(head, base + Vector3(0.0, 4.3, 0.0), _lamp_head_mat)
	var light := OmniLight3D.new()
	light.position = base + Vector3(0.0, 4.0, 0.0)
	light.omni_range = 11.0
	light.light_energy = 2.5
	light.light_color = Color(1.0, 0.72, 0.4)
	add_child(light)
	_night_lights.append(light)


func _add_bikes(x: float, side: float) -> void:
	for i in _rng.randi_range(2, 5):
		var jitter := _rng.randf_range(-0.12, 0.12)
		_add_sprite("bicycle", Vector3(x + i * 0.75, 0.04, side * (CANAL_HALF + 1.6)), jitter)


func _add_parked_car(pos: Vector3) -> void:
	var car: String = PARKED_CARS[_rng.randi() % PARKED_CARS.size()]
	_add_sprite(car, pos + Vector3(0.0, 0.06, 0.0), PI / 2.0 * signf(pos.z))
	_add_static_box(Vector3(3.8, 2.0, 2.0), pos + Vector3(0.0, 1.0, 0.0))


func _build_tram() -> void:
	var tile := ArtDb.meters(ArtDb.entry("textures", "tram_tracks"), "meters")
	# The rails in tram_tracks.png sit at about 76% of the tile width.
	_tram = _add_sprite("tram", Vector3(TRAM_X + tile.x * 0.76, 0.1, 20.0), 0.0)


func _move_tram(delta: float) -> void:
	var z := _tram.position.z + _tram_dir * 7.0 * delta
	if absf(z) > Z_EXTENT - 12.0:
		_tram_dir = -_tram_dir
	_tram.position.z = clampf(z, -(Z_EXTENT - 12.0), Z_EXTENT - 12.0)
	_tram.rotation.y = 0.0 if _tram_dir < 0.0 else PI


## Placeholder players: one per colour, pacing back and forth on the sidewalk.
func _build_players() -> void:
	for i in PLAYER_COLORS.size():
		var color: String = PLAYER_COLORS[i]
		var start := Vector3(-28.0 + i * 3.4, 0.08, -16.4 + (i % 2) * 0.9)
		var sprite := _add_sprite("player_stand_" + color, start, 0.0)
		_walkers.append([sprite, color, start.x, i * 1.3])


func _move_walkers(delta: float) -> void:
	_walk_time += delta
	for w: Array in _walkers:
		var sprite: PixelSprite = w[0]
		var t: float = _walk_time + w[3]
		# Walk 3 m east, then 3 m back, swinging arms on alternate steps.
		var span := 3.0 / WALK_SPEED
		var leg := fmod(t, span * 2.0)
		var east := leg < span
		var along := leg if east else span * 2.0 - leg
		sprite.position.x = w[2] + along * WALK_SPEED
		sprite.rotation.y = -PI / 2.0 if east else PI / 2.0
		var step := int(t / STEP_TIME) % 2
		var frame := "player_walk_" if step == 0 else "player_stand_"
		var asset := ArtDb.entry("sprites", frame + str(w[1]))
		sprite.set_asset(asset)
		sprite.flip_h = int(t / (STEP_TIME * 2.0)) % 2 == 1


func _build_bounds() -> void:
	var w := X_MAX - X_MIN
	var cx := (X_MIN + X_MAX) / 2.0
	_add_static_box(Vector3(w, 4.0, 1.0), Vector3(cx, 2.0, -Z_EXTENT))
	_add_static_box(Vector3(w, 4.0, 1.0), Vector3(cx, 2.0, Z_EXTENT))
	_add_static_box(Vector3(1.0, 4.0, Z_EXTENT * 2.0), Vector3(X_MIN, 2.0, 0.0))
	_add_static_box(Vector3(1.0, 4.0, Z_EXTENT * 2.0), Vector3(X_MAX, 2.0, 0.0))


func _build_hud() -> void:
	# Added outside the low-res SubViewport so the text stays sharp.
	var layer := CanvasLayer.new()
	_view.add_child.call_deferred(layer)
	_hud = Label.new()
	_hud.position = Vector2(16.0, 12.0)
	_hud.add_theme_font_size_override("font_size", 18)
	_hud.add_theme_constant_override("outline_size", 6)
	_hud.add_theme_color_override("font_outline_color", Color.BLACK)
	layer.add_child(_hud)


# --- helpers --------------------------------------------------------------

## Splits [a, b] around the street gaps, keeping `margin` metres clear.
func _segments(a: float, b: float, margin: float) -> Array[Vector2]:
	var out: Array[Vector2] = []
	var start := a
	for street: Vector2 in STREETS:
		if street.x - margin > start:
			out.append(Vector2(start, street.x - margin))
		start = street.y + margin
	if b > start:
		out.append(Vector2(start, b))
	return out


## Material that tiles a texture in world space at its real-world size.
func _world_mat(tex_name: String) -> ShaderMaterial:
	var asset := ArtDb.entry("textures", tex_name)
	return PixelMaterials.world(ArtDb.texture(asset), ArtDb.meters(asset, "meters"))


func _color_mat(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	return mat


func _add_sprite(sprite_name: String, pos: Vector3, yaw: float) -> PixelSprite:
	var sprite := PixelSprite.new()
	sprite.set_asset(ArtDb.entry("sprites", sprite_name))
	sprite.position = pos
	sprite.rotation.y = yaw
	add_child(sprite)
	return sprite


func _add_mesh(mesh: Mesh, pos: Vector3, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	add_child(mi)
	return mi


func _add_box(size: Vector3, pos: Vector3, mat: Material) -> MeshInstance3D:
	var box := BoxMesh.new()
	box.size = size
	return _add_mesh(box, pos, mat)


func _add_plane(size: Vector2, pos: Vector3, mat: Material) -> MeshInstance3D:
	var plane := PlaneMesh.new()
	plane.size = size
	return _add_mesh(plane, pos, mat)


func _add_static_box(size: Vector3, pos: Vector3) -> void:
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	body.position = pos
	add_child(body)
