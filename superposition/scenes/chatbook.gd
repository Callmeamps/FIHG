extends Control

@onready var message_list: VBoxContainer = %MessageList
@onready var input: LineEdit = %Input

func _ready():
	%SendBtn.pressed.connect(_on_send)

func _on_send():
	var text = input.text.strip_edges()
	if text.is_empty():
		return
	_add_message("user", text)
	input.clear()

func _add_message(sender: String, text: String):
	var label = Label.new()
	label.text = "[%s] %s" % [sender, text]
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	message_list.add_child(label)