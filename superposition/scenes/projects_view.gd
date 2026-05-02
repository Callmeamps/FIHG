extends Control

# Placeholder projects list view.
# Real implementation: fetch projects from API, show in a list, allow create/navigate.

var _projects: Array = []
var _http: HTTPRequest = null

@onready var list: VBoxContainer = %ProjectList
@onready var create_btn: Button = %CreateBtn
@onready var create_input: LineEdit = %CreateInput

func _ready():
	create_btn.pressed.connect(_on_create_project)
	_fetch_projects()

func _fetch_projects():
	_http = HTTPRequest.new()
	add_child(_http)
	_http.request_completed.connect(_on_projects_loaded)
	var err = _http.request("http://127.0.0.1:8000/projects")
	if err != OK:
		push_warning("Failed to request projects: %d" % err)

func _on_projects_loaded(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	if _code != 200:
		push_warning("Projects load failed: %d" % _code)
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Array:
		_projects = json
		_refresh_list()

func _refresh_list():
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()
	for p in _projects:
		var btn = Button.new()
		btn.text = p.get("title", "(untitled)")
		btn.pressed.connect(_on_project_clicked.bind(p))
		list.add_child(btn)

func _on_project_clicked(project: Dictionary):
	# Populate the inspector panel with project details
	var main = get_node("/root/Main")
	if main and main.has_method("inspect"):
		main.inspect("project", project.get("id", ""))

func _on_create_project():
	var title = create_input.text.strip_edges()
	if title.is_empty():
		return
	create_input.clear()
	var payload = JSON.stringify({"title": title})
	var h = HTTPRequest.new()
	add_child(h)
	h.request_completed.connect(_on_project_created)
	h.request("http://127.0.0.1:8000/projects", ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_project_created(_result: int, _code: int, _headers: PackedStringArray, _body: PackedByteArray):
	if _code in [200, 201]:
		_fetch_projects()
	else:
		push_warning("Create project failed: %d" % _code)