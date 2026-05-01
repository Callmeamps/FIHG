extends Control

# Superposition main controller.
# Routes signals from left rail navigation to swap center viewport content.
# Terminal dock at bottom is always visible.
# Talks to Python core at http://127.0.0.1:8000

const API_BASE = "http://127.0.0.1:8000"
const WS_URL = "ws://127.0.0.1:8000/ws"

var ws: WebSocketPeer = null

@onready var left_rail: VBoxContainer = %LeftRail
@onready var center_viewport: Control = %CenterViewport
@onready var terminal_dock: Control = %TerminalDock

var current_panel: Control = null
var dashboard_scene = preload("res://scenes/dashboard.tscn")
var chatbook_scene = preload("res://scenes/chatbook.tscn")

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

func switch_panel(panel: Control):
	if current_panel:
		center_viewport.remove_child(current_panel)
		current_panel.queue_free()
	center_viewport.add_child(panel)
	panel.anchor_right = 1.0
	panel.anchor_bottom = 1.0
	current_panel = panel

# --- WebSocket connection ---

func connect_ws():
	ws = WebSocketPeer.new()
	var err = ws.connect_to_url(WS_URL)
	if err != OK:
		push_warning("WS connect failed: ", err)

func _process(_delta):
	if ws and ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		ws.poll()
		while ws.get_available_packet_count() > 0:
			var pkt = ws.get_packet().get_string_from_utf8()
			var data = JSON.parse_string(pkt)
			_handle_ws_message(data)

func _handle_ws_message(data: Dictionary):
	if data.get("type") == "terminal:output":
		# Forward to terminal panel if visible
		var tp = terminal_dock.get_child(0) if terminal_dock.get_child_count() > 0 else null
		if tp and tp.has_method("on_terminal_output"):
			tp.on_terminal_output(data.get("data", ""))
	elif data.get("type") == "pong":
		pass

func send_ws(data: Dictionary):
	if ws and ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		ws.send_text(JSON.stringify(data))

func _exit_tree():
	if ws:
		ws.close()