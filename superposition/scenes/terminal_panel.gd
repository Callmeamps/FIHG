extends Control

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
	http.request("http://127.0.0.1:8000/terminal/spawn", [], HTTPClient.METHOD_POST, '{"command":"/bin/bash"}')

func _on_session_created(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json and json.has("session_id"):
		session_id = json["session_id"]
		output.append_text("[color=green]Session %s started[/color]\n" % session_id)

func _on_send():
	var cmd = input.text.strip_edges()
	if cmd.is_empty():
		return
	input.clear()
	output.append_text("[color=yellow]$ %s[/color]\n" % cmd)

	# Send via HTTP POST to the terminal API
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_write_done)
	var url = "http://127.0.0.1:8000/terminal/%s/write" % session_id
	var payload = '{"data":"%s\\n"}' % cmd.replace("\\", "\\\\").replace('"', '\\"')
	http.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_write_done(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	# Then fetch the buffer
	_fetch_output()

func _fetch_output():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_output_fetched)
	http.request("http://127.0.0.1:8000/terminal/sessions")

func _on_output_fetched(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json and json.has("sessions"):
		for s in json["sessions"]:
			if s["id"] == session_id:
				# Refresh — in real impl we'd stream via WS
				output.append_text("[color=gray](output available via WS)[/color]\n")

func on_terminal_output(data: String):
	output.append_text(data)