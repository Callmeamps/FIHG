extends Control

const API_BASE = "http://127.0.0.1:8000"

@onready var title: Label = %Title

var _http: HTTPRequest = null

func _ready():
	_fetch_status()

func _fetch_status():
	_http = HTTPRequest.new()
	add_child(_http)
	_http.request_completed.connect(_on_status_loaded)
	var err = _http.request("%s/health" % API_BASE)
	if err != OK:
		push_warning("Health check failed: %d" % err)

func _on_status_loaded(result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	var status = "[color=green]OK[/color]"
	if result != 0 or _code != 200:
		status = "[color=red]Unreachable[/color]"
	else:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json is Dictionary:
			status = "[color=green]%s[/color]" % json.get("status", "ok")
	var note = "\n[Status: %s]\n\nBackend: healthy check\nProjects: (open Projects view)\nTasks: requires GET /tasks (not yet implemented)" % status
	title.text = "Dashboard%s" % note
	title.vertical_alignment = Label.VALIGN_TOP
	title.text_direction = Control.TEXT_DIRECTION_LTR