extends Control

@onready var message_list: VBoxContainer = %MessageList
@onready var input: LineEdit = %Input
@onready var send_btn: Button = %SendBtn

var chatbook_id: String = ""

func _ready():
	send_btn.pressed.connect(_on_send)
	_create_or_load_chatbook()

func _create_or_load_chatbook():
	# For now, create a chatbook under the first project
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_projects_fetched)
	http.request("http://127.0.0.1:8000/projects")

func _on_projects_fetched(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Array and json.size() > 0:
		var project_id = json[0]["id"]
		_create_chat(project_id)
	else:
		# No projects yet, create one
		var http = HTTPRequest.new()
		add_child(http)
		http.request_completed.connect(_on_project_created)
		http.request("http://127.0.0.1:8000/projects", ["Content-Type: application/json"], HTTPClient.METHOD_POST, '{"title":"Default"}')

func _on_project_created(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json and json.has("id"):
		_create_chat(json["id"])

func _create_chat(project_id: String):
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_chat_created)
	var payload = '{"project_id":"%s","title":"Main Chat"}' % project_id
	http.request("http://127.0.0.1:8000/chatbooks", ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_chat_created(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json and json.has("id"):
		chatbook_id = json["id"]
		_load_messages()

func _load_messages():
	if chatbook_id.is_empty():
		return
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_messages_loaded)
	http.request("http://127.0.0.1:8000/chatbooks/%s/messages" % chatbook_id)

func _on_messages_loaded(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Array:
		for child in message_list.get_children():
			message_list.remove_child(child)
			child.queue_free()
		for msg in json:
			_add_message(msg["role"], msg["content"])

func _on_send():
	var text = input.text.strip_edges()
	if text.is_empty() or chatbook_id.is_empty():
		return
	input.clear()
	_add_message("user", text)

	# Send to API
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_message_sent)
	var payload = '{"role":"user","content":"%s"}' % text.replace("\\", "\\\\").replace('"', '\\"')
	http.request("http://127.0.0.1:8000/chatbooks/%s/messages" % chatbook_id,
		["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_message_sent(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	pass  # Already added locally

func _add_message(role: String, text: String):
	var label = Label.new()
	label.text = "[%s] %s" % [role, text]
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.custom_minimum_size = Vector2(0, 24)
	message_list.add_child(label)