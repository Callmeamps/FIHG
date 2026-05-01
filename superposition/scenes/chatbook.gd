extends Control

const API_BASE = "http://127.0.0.1:8000"

@onready var message_list: VBoxContainer = %MessageList
@onready var input: LineEdit = %Input
@onready var send_btn: Button = %SendBtn

var chatbook_id: String = ""

func _ready():
	send_btn.pressed.connect(_on_send)
	_create_or_load_chatbook()

func _create_or_load_chatbook():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_projects_fetched)
	var err = http.request("%s/projects" % API_BASE)
	if err != OK:
		push_warning("Failed to fetch projects: %d" % err)

func _on_projects_fetched(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	if _code != 200:
		push_warning("Projects fetch failed: %d" % _code)
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Array and json.size() > 0:
		_create_chat(json[0]["id"])
	else:
		var http = HTTPRequest.new()
		add_child(http)
		http.request_completed.connect(_on_project_created)
		var payload = JSON.stringify({"title": "Default"})
		http.request("%s/projects" % API_BASE, ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_project_created(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	if _code not in [200, 201]:
		push_warning("Project create failed: %d" % _code)
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Dictionary and json.has("id"):
		_create_chat(json["id"])
	else:
		push_warning("Project create returned invalid JSON")

func _create_chat(project_id: String):
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_chat_created)
	var payload = JSON.stringify({"project_id": project_id, "title": "Main Chat"})
	http.request("%s/chatbooks" % API_BASE, ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_chat_created(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	if _code not in [200, 201]:
		push_warning("Chatbook create failed: %d" % _code)
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Dictionary and json.has("id"):
		chatbook_id = json["id"]
		_load_messages()

func _load_messages():
	if chatbook_id.is_empty():
		return
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_messages_loaded)
	http.request("%s/chatbooks/%s/messages" % [API_BASE, chatbook_id])

func _on_messages_loaded(_result: int, _code: int, _headers: PackedStringArray, body: PackedByteArray):
	if _code != 200:
		push_warning("Messages load failed: %d" % _code)
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Array:
		for child in message_list.get_children():
			message_list.remove_child(child)
			child.queue_free()
		for msg in json:
			_add_message(msg.get("role", "?"), msg.get("content", ""))

func _on_send():
	var text = input.text.strip_edges()
	if text.is_empty() or chatbook_id.is_empty():
		return
	input.clear()
	_add_message("user", text)

	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_message_sent)
	var payload = JSON.stringify({"role": "user", "content": text})
	var url = "%s/chatbooks/%s/messages" % [API_BASE, chatbook_id]
	http.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, payload)

func _on_message_sent(_result: int, _code: int, _headers: PackedStringArray, _body: PackedByteArray):
	if _code not in [200, 201]:
		push_warning("Message send failed: %d" % _code)
	# Already added locally

func _add_message(role: String, text: String):
	var label = Label.new()
	label.text = "[%s] %s" % [role, text]
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.custom_minimum_size = Vector2(0, 24)
	message_list.add_child(label)