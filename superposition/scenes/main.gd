extends Control

# Superposition main controller.
# Routes signals from left rail navigation to swap center viewport content.
# Terminal dock at bottom is always visible.

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