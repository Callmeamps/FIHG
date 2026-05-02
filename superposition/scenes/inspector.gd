extends Control

# Inspector panel — displays metadata for the currently selected entity.
# Populated by signals from other panels (dashboard, projects, etc.).

const API_BASE = "http://127.0.0.1:8000"

@onready var type_label: Label = %TypeLabel
@onready var id_label: Label = %IdLabel
@onready var prop_container: VBoxContainer = %PropContainer
@onready var refresh_btn: Button = %RefreshBtn

var _entity_type: String = ""
var _entity_id: String = ""

func _ready():
	refresh_btn.pressed.connect(_refresh)
	show_empty()

func show_empty():
	_entity_type = ""
	_entity_id = ""
	type_label.text = "Inspector"
	id_label.text = "(no selection)"
	_clear_props()
	_add_prop_row("hint", "Select an item from any panel to inspect its details")

# --- Called by other panels when user clicks an item ---

func inspect(entity_type: String, entity_id: String):
	_entity_type = entity_type
	_entity_id = entity_id
	type_label.text = entity_type.capitalize()
	id_label.text = entity_id
	_clear_props()
	_add_prop_row("loading", "Loading...")
	_fetch_entity()

func _fetch_entity():
	if _entity_type.is_empty() or _entity_id.is_empty():
		return
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_entity_loaded)
	var endpoint = "/%s/%s" % [_entity_type, _entity_id]
	var err = http.request("%s%s" % [API_BASE, endpoint])
	if err != OK:
		push_warning("inspector fetch failed: %d" % err)

func _on_entity_loaded(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray):
	_clear_props()
	if code != 200:
		_add_prop_row("error", "Not found (HTTP %d)" % code)
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Dictionary:
		_show_props(json)
	else:
		_add_prop_row("raw", str(json))

func _show_props(data: Dictionary):
	# Sort keys: id, name/title first, then status, then rest
	var priority_keys = ["id", "title", "name", "status", "description", "created_at"]
	for key in priority_keys:
		if key in data:
			_add_prop_row(key, str(data[key]))
	for key in data.keys():
		if not key in priority_keys:
			var val = data[key]
			if val != null:
				_add_prop_row(key, str(val))

func _refresh():
	if _entity_type.is_empty():
		return
	_clear_props()
	_add_prop_row("loading", "Loading...")
	_fetch_entity()

func _clear_props():
	for child in prop_container.get_children():
		prop_container.remove_child(child)
		child.queue_free()

func _add_prop_row(key: String, value: String):
	var row = HBoxContainer.new()
	row.set("custom_constants/separation", 8)

	var key_label = Label.new()
	key_label.text = "%s:" % key
	key_label.custom_minimum_size = Vector2(140, 0)
	key_label.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN

	var val_label = Label.new()
	val_label.text = value
	val_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	val_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

	if key == "error":
		val_label.add_theme_color_override("font_color", Color(1, 0.3, 0.3))
	elif key == "loading":
		val_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
		val_label.text = "…"
	elif key == "hint":
		val_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.5))
	elif key == "id":
		val_label.add_theme_color_override("font_color", Color(0.6, 0.6, 1.0))
	elif key in ["status", "mode"]:
		var color = Color(0.7, 1.0, 0.7) if value in ["idle", "active", "done"] else Color(1.0, 0.9, 0.5)
		val_label.add_theme_color_override("font_color", color)
	else:
		val_label.add_theme_color_override("font_color", Color(0.85, 0.85, 0.85))

	row.add_child(key_label)
	row.add_child(val_label)
	prop_container.add_child(row)