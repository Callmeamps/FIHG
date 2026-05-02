extends Control

# Activity panel — live feed of recent system events from /logs.
# Polls every 5 seconds, newest first.

const API_BASE = "http://127.0.0.1:8000"
const POLL_INTERVAL = 5.0

@onready var feed: VBoxContainer = %Feed
@onready var filter_type: OptionButton = %FilterType
@onready var filter_event: LineEdit = %FilterEvent
@onready var poll_timer: Timer = %PollTimer
@onready var empty_label: Label = %EmptyLabel

var _filter_type: String = ""

func _ready():
	poll_timer.timeout.connect(_poll)
	filter_event.text_submitted.connect(_on_filter_event)
	# Populate type filter dropdown
	filter_type.add_item("all")
	var types = ["project", "task", "agent", "approval", "chatbook", "artifact", "run", "process"]
	for t in types:
		filter_type.add_item(t)
	filter_type.item_selected.connect(_on_filter_type)
	_start_polling()

func _start_polling():
	_poll()
	poll_timer.start(POLL_INTERVAL)

func _poll():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_logs_loaded)
	var url = "%s/logs?limit=50" % API_BASE
	if not _filter_type.is_empty() and _filter_type != "all":
		url += "&entity_type=%s" % _filter_type
	var event_filter = filter_event.text.strip_edges()
	if not event_filter.is_empty():
		url += "&event=%s" % event_filter.uri_encode()
	http.request(url)

func _on_logs_loaded(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray):
	if code != 200:
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json is Array:
		_refresh_feed(json)

func _refresh_feed(entries: Array):
	# Preserve scroll position if user scrolled up
	var at_bottom = feed.get_parent().get_v_scroll() >= feed.get_parent().get_v_scroll_max() - 10
	_clear_feed()
	if entries.is_empty():
		empty_label.visible = true
		return
	empty_label.visible = false
	for entry in entries:
		_add_entry(entry)
	if at_bottom:
		await get_tree().process_frame
		feed.get_parent().set_v_scroll(feed.get_parent().get_v_scroll_max())

func _clear_feed():
	for child in feed.get_children():
		feed.remove_child(child)
		child.queue_free()

func _add_entry(entry: Dictionary):
	var row = HBoxContainer.new()
	row.set("custom_constants/separation", 6)

	# Timestamp
	var time_label = Label.new()
	var ts = entry.get("created_at", "")
	if ts != "":
		# Show HH:MM:SS from ISO8601
		if ts.length() >= 19:
			time_label.text = ts.substr(11, 8)
		else:
			time_label.text = ts
	else:
		time_label.text = "??:??:??"
	time_label.add_theme_color_override("font_color", Color(0.4, 0.4, 0.4))
	time_label.custom_minimum_size = Vector2(70, 0)

	# Event type badge
	var event = entry.get("event", "?")
	var event_label = Label.new()
	event_label.text = _abbrev(event)
	event_label.add_theme_color_override("font_color", _event_color(event))
	event_label.custom_minimum_size = Vector2(130, 0)

	# Entity
	var entity_label = Label.new()
	entity_label.text = "[%s]" % entry.get("entity_type", "?")
	entity_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	entity_label.custom_minimum_size = Vector2(90, 0)

	# Detail
	var detail_label = Label.new()
	var detail = entry.get("detail", {})
	var detail_str = ""
	if detail is Dictionary:
		if "reason" in detail:
			detail_str = detail["reason"]
		elif "by" in detail:
			detail_str = "(by %s)" % detail["by"]
	var eid = entry.get("entity_id", "")
	if detail_str.is_empty():
		detail_str = eid.substr(0, 8) if eid else ""
	detail_label.text = detail_str
	detail_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detail_label.add_theme_color_override("font_color", Color(0.75, 0.75, 0.75))

	row.add_child(time_label)
	row.add_child(event_label)
	row.add_child(entity_label)
	row.add_child(detail_label)
	feed.add_child(row)

func _abbrev(event: String) -> String:
	var abbrevs = {
		"project.created": "project:created",
		"task.created": "task:created",
		"task.paused": "task:paused",
		"task.resumed": "task:resumed",
		"task.cancelled": "task:cancelled",
		"task.done": "task:done",
		"agent.created": "agent:created",
		"agent.idle": "agent:idle",
		"agent.busy": "agent:busy",
		"approval.created": "approval:created",
		"approval.responded": "approval:done",
		"run.started": "run:started",
		"run.finished": "run:finished",
	}
	return abbrevs.get(event, event)

func _event_color(event: String) -> Color:
	if event.begins_with("task."):
		return Color(0.4, 0.75, 1.0)
	if event.begins_with("agent."):
		return Color(0.75, 0.6, 1.0)
	if event.begins_with("approval."):
		return Color(1.0, 0.6, 0.3)
	if event.begins_with("project."):
		return Color(0.5, 1.0, 0.6)
	if event.begins_with("run."):
		return Color(0.6, 1.0, 0.9)
	return Color(0.7, 0.7, 0.7)

func _on_filter_type(idx: int):
	var selected = filter_type.get_item_text(idx)
	_filter_type = selected if selected != "all" else ""
	_start_polling()

func _on_filter_event(text: String):
	_start_polling()