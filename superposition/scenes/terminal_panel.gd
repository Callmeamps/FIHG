extends Control

@onready var output: RichTextLabel = %Output
@onready var input: LineEdit = %Input

func _ready():
	%SendBtn.pressed.connect(_on_send)

func _on_send():
	var cmd = input.text.strip_edges()
	if cmd.is_empty():
		return
	output.append_text("[color=yellow]$ %s[/color]\n" % cmd)
	input.clear()
	# TODO: send command to Python terminal runtime via HTTP/WS