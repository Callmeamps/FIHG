extends Control

const API_BASE = "http://127.0.0.1:8000"

@onready var output: RichTextLabel = %Output
@onready var input: LineEdit = %Input
@onready var send_btn: Button = %SendBtn

var session_id: String = ""

func _ready():
	send_btn.pressed.connect(_on_send)
	_spawn_session()

func _spawn_session():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_session_created)
	var payload = JSON.stringify({"command": "/bin/bash"})
	http.request("%s/terminal/spawn" % API_BASE, ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_session_created(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	if _code not in [200, 201]:
		push_warning("Session spawn failed: %d" % _code)
		output.append_text("[color=red]Failed to start terminal session[/color]\n")
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Dictionary and json.has("session_id"):
		session_id = json["session_id"]
		output.append_text("[color=green]Session %s started[/color]\n" % session_id)
	else:
		push_warning("Session spawn returned invalid JSON")
		output.append_text("[color=red]Invalid session response[/color]\n")

func _on_send():
	var cmd = input.text.strip_edges()
	if cmd.is_empty():
		return
	if session_id.is_empty():
		output.append_text("[color=red]No active session[/color]\n")
		return
	input.clear()
	output.append_text("[color=yellow]$ %s[/color]\n" % cmd)

	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_write_done)
	var payload = JSON.stringify({"data": cmd + "\n"})
	http.request("%s/terminal/%s/write" % [API_BASE, session_id], ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_write_done(_result: int, _code: int, _headers: PackedStringArray, _body: PackedByteArray):
	if _code != 200:
		push_warning("Terminal write failed: %d" % _code)

# Called from main.gd when WS delivers terminal:output
func on_terminal_output(data: String):
	if data.is_empty():
		return
	# Color stderr red, stdout white
	if data.begins_with("\x1b[31m") or "[error]" in data:
		output.append_text("[color=red]%s[/color]" % data)
	else:
		output.append_text("%s" % data)