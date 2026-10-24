class_name GtaCamera
extends Camera3D
## GTA 2 style camera. Looks straight down from above the target, rises a
## little with the target's speed and leads ahead of it.

@export var target_path: NodePath
@export var base_height := 21.0
@export var height_per_speed := 0.35
@export var max_extra_height := 8.0
@export var lead_seconds := 0.5
@export var follow_sharpness := 4.0

var _height := 0.0
var _lead := Vector3.ZERO

@onready var _target: Node3D = get_node(target_path)


func _ready() -> void:
	fov = 55.0
	near = 1.0
	far = 300.0
	rotation = Vector3(-PI / 2.0, 0.0, 0.0)
	_height = base_height


func _process(delta: float) -> void:
	var k := 1.0 - exp(-follow_sharpness * delta)
	var speed := 0.0
	var velocity := Vector3.ZERO
	if _target is Car:
		speed = absf((_target as Car).speed)
		velocity = (_target as Car).velocity
	var wanted_height := base_height + minf(speed * height_per_speed, max_extra_height)
	_height = lerpf(_height, wanted_height, k * 0.5)
	_lead = _lead.lerp(velocity * lead_seconds, k)
	global_position = _target.global_position + _lead + Vector3(0.0, _height, 0.0)
