class_name Car
extends CharacterBody3D
## Arcade top-down car on the ground plane (x/z). Forward is -Z.
## Prototype input: WASD or arrow keys. Touch controls come later.

@export var max_speed := 24.0
@export var max_reverse := 7.0
@export var acceleration := 11.0
@export var braking := 28.0
@export var rolling_drag := 4.0
@export var turn_rate := 2.6

var speed := 0.0
var heading := 0.0

var _headlights: Array[SpotLight3D] = []

@onready var _sprite: Sprite3D = $Sprite


func _ready() -> void:
	motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	_sprite.pixel_size = ArtDb.pixel_size()
	_sprite.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	for side: float in [-0.6, 0.6]:
		var light := SpotLight3D.new()
		light.position = Vector3(side, 0.8, -1.9)
		light.rotation_degrees = Vector3(-12.0, 0.0, 0.0)
		light.spot_range = 18.0
		light.spot_angle = 28.0
		light.light_energy = 4.0
		light.light_color = Color(1.0, 0.95, 0.8)
		light.visible = false
		add_child(light)
		_headlights.append(light)


func set_headlights(on: bool) -> void:
	for light in _headlights:
		light.visible = on


func _physics_process(delta: float) -> void:
	var throttle := _key(KEY_W, KEY_UP) - _key(KEY_S, KEY_DOWN)
	var steer := _key(KEY_D, KEY_RIGHT) - _key(KEY_A, KEY_LEFT)
	if throttle > 0.0:
		speed += (braking if speed < 0.0 else acceleration) * delta
	elif throttle < 0.0:
		speed -= (braking if speed > 0.0 else acceleration) * delta
	else:
		speed = move_toward(speed, 0.0, rolling_drag * delta)
	speed = clampf(speed, -max_reverse, max_speed)

	# Steering only bites when moving, and flips when reversing.
	var grip := clampf(absf(speed) / 5.0, 0.0, 1.0) * signf(speed)
	heading -= steer * turn_rate * grip * delta
	rotation = Vector3(0.0, heading, 0.0)

	velocity = -global_basis.z * speed
	move_and_slide()
	if get_slide_collision_count() > 0:
		speed *= 0.6
	position.y = 0.0


func _key(a: Key, b: Key) -> float:
	return 1.0 if Input.is_physical_key_pressed(a) or Input.is_physical_key_pressed(b) else 0.0
