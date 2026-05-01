extends Control

# Superposition main controller.
# Routes signals from left rail navigation to swap center viewport content.
# Terminal dock at bottom is always visible.
# Talks to Python core at http://127.0.0.1:8000

const API_BASE = "http://127.0.0.1:8000"
const WS_URL = "ws://127.0.0.1:8000/ws"

var ws: WebSocketPeer = null
var ws_reconnect_delay: float = 1.0
var ws_max_delay: float = 30.0
var ws_retrying: bool = false

@onready var left_rail: VBoxContainer = %LeftRail
@onready var center_viewport: Control = %CenterViewport
@onready var terminal_dock: Control = %TerminalDock

var current_panel: Control = null
var dashboard_scene = preload("res://scenes/dashboard.tscn")
var chatbook_scene = preload("res://scenes/chatbook.tscn")
var projects_scene = preload("res://scenes/projects_view.tscn")

func _ready():
	for button in left_rail.get_children():
		if button is Button:
			button.pressed.connect(_on_nav_clicked.bind(button))
	connect_ws()

func _on_nav_clicked(button: Button):
	match button.text:
		"Dashboard":
			switch_panel(dashboard_scene.instantiate())
		"Chatbooks":
			switch_panel(chatbook_scene.instantiate())
		"Projects":
			switch_panel(projects_scene.instantiate())
		"Agents":
			# Placeholder — agent system not yet implemented
			push_warning("Agents view not implemented yet")

# --- WebSocket connection with reconnect ---

func connect_ws():
	ws = WebSocketPeer.new()
	var err = ws.connect_to_url(WS_URL)
	if err != OK:
		push_warning("WS connect failed: %d" % err)
		_schedule_reconnect()

func _schedule_reconnect():
	if ws_retrying:
		return
	ws_retrying = true
	await get_tree().create_timer(ws_reconnect_delay).timeout
	ws_retrying = false
	ws_reconnect_delay = min(ws_reconnect_delay * 2, ws_max_delay)
	connect_ws()

func _process(_delta):
	if ws == null:
		return
	match ws.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			ws.poll()
			while ws.get_available_packet_count() > 0:
				var pkt = ws.get_packet().get_string_from_utf8()
				var data = JSON.parse_string(pkt)
				if data is Dictionary:
					_handle_ws_message(data)
		WebSocketPeer.STATE_CLOSED:
			if not ws_retrying:
				_schedule_reconnect()

func _handle_ws_message(data: Dictionary):
	match data.get("type"):
		"terminal:output":
			var tp = terminal_dock.get_child(0) if terminal_dock.get_child_count() > 0 else null
			if tp and tp.has_method("on_terminal_output"):
				tp.on_terminal_output(data.get("data", ""))
		"pong":
			pass
		_:
			push_warning("Unknown WS message type: %s" % str(data.get("type")))

func send_ws(data: Dictionary):
	if ws and ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		ws.send_text(JSON.stringify(data))

func _exit_tree():
	if ws:
		ws.close()