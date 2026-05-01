# Scratchpad — Superposition

Observations, potential improvements, known issues, and design notes collected during development.
Not a todo list — these are things to consider revisiting.

---

## Python Backend

### Architecture & Code Quality

- **`_run_cell()` duplicates subprocess logic** for shell vs python. Should use a dispatch dict: `{"shell": bash -c, "python": python3 -c}`.
- **`subprocess.run()` blocks the async event loop.** FastAPI runs sync endpoints in a threadpool, but `_run_cell()` is called from an async handler via `await`. Under load, 30s timeouts could starve the thread pool. Should use `asyncio.create_subprocess_exec()` or push to a background worker.
- **`datetime.utcnow()` is deprecated** across models.py, main.py, terminal.py. Should use `datetime.now(datetime.UTC)`. Cosmetic but noisy in test output.
- **No `DELETE /artifacts/{id}` or `PUT /artifacts/{id}` endpoints.** Create and list exist, but no update or delete via API.
- **No `GET /chatbooks/{id}` single-chatbook endpoint.** Only list-all and messages. Could be useful for Godot navigation.
- **`GET /tasks` endpoint missing.** Only `POST /tasks` exists. No way to list/filter tasks.
- **`source_ref` in Artifact is an unvalidated string.** Could reference a non-existent cell/message. Consider a FK or at least format validation.
- **Cell execution doesn't create a `Run` record.** The `cell.run` relationship exists but `_run_cell()` returns output directly instead of creating a Process + Run chain. This breaks the execution provenance model.
- **No cell `DELETE` or `PUT`.** Can't edit/retry a cell once executed.
- **`terminal_runtime` is a global mutable.** Not great for test isolation. Tests share the same runtime instance.
- **No rate limiting or auth.** Every endpoint is wide open. Fine for a prototype, but needs CORS/middleware for real use.
- **`get_session` commits on every yield.** If an exception occurs after yield but before the `except` block catches it, the session may be in an inconsistent state. The `finally: session.close()` is safe, but the rollback/commit logic is fragile with FastAPI's dependency injection.

### Testing

- **`test_models.py` uses `AsyncSessionLocal` directly** instead of the `get_session` dependency. Works but inconsistent with API tests.
- **No test for cell execution with unknown language** (regression: should return error, not crash).
- **No test for `create-task` with non-existent message** (404 case).
- **No test for artifact filtering by `task_id`**.
- **No test for terminal write to non-existent session** (error case).

---

## Godot Frontend

### Scene Architecture

- **`chatbook.gd` creates chatbooks via API on every load** rather than letting the user pick one. Hardcoded "Default" project. No project selector or chatbook list view.
- **`terminal_panel.gd` fetches output by polling `/terminal/sessions`** instead of using the WebSocket. The WS stream is wired up in `main.gd` but `terminal_panel.gd` doesn't listen for it properly. The `on_terminal_output()` method exists but is called from `main.gd` with no guarantee the terminal panel is the active child.
- **`dashboard.gd` is empty.** No data binding, no task list, no stats. Placeholder.
- **No cell UI at all.** `Chatbook.tscn` has messages but cells (the chat+code blocks) have no Godot representation. Output from cell execution is stored in the DB but invisible in the UI.
- **Left rail buttons with no handlers** ("Projects", "Agents" buttons in `main.tscn` exist but aren't handled in `main.gd` — only Dashboard and Chatbooks have navigation).
- **No error handling in any GDScript.** HTTP requests can fail, JSON parse can fail, sessions can be missing. All silently swallowed.
- **WS reconnect logic missing.** If the server restarts, `main.gd` tries once and never retries.
- **Layout is hardcoded in tscn files** (anchor presets, pixel offsets). No responsive layout or theme system. Resize the window and it breaks.
- **`chatbook.gd` creates a new `HTTPRequest` per API call.** No pooling or reuse. Won't leak but it's lazy.

### Godot-Specific Issues

- **`project.godot` declares C# project** (`[dotnet] project/assembly_name="Superposition"`) but all scenes are GDScript. The C# flag may cause issues on systems without .NET SDK. Should remove the dotnet section.
- **Rendering set to "GL Compatibility"** but the scene uses no 3D. Fine for 2D UI, but the Jolt Physics engine is loaded unnecessarily.
- **No icon/export preset configured.** Can't build without additional setup.

---

## Ubiquitous Language

### Terms That Need Better Definition

- **"Process" vs "Run"** distinction is clear in the design doc but muddy in practice. `Process` tracks an OS-level PTY session. `Run` tracks an execution record. But `Cell.run` relationship is `uselist=False` (one Run per Cell), while `Process.runs` is a list. The asymmetry makes sense (one cell = one execution attempt) but could confuse.
- **"Cell" is a `language` field with only "shell" and "python"** — no extensibility story for adding SQL, JavaScript, etc. The `_run_cell()` dispatch is hardcoded.
- **`Chatbook.lane_id` is nullable and unused** in the current API. The Lane <-> Chatbook association exists in the schema but no API endpoints reference it.

### Docs Drift

- **`UBIQUITOUS_LANGUAGE.md` doesn't list "Cell"** — it was added after the language audit. Should be documented alongside Message, Chatbook.
- **Design doc mentions "agent scheduler and queue system"** but this doesn't exist yet. The `agent/superposition_design_doc.md` describes it as Phase 3.

---

## Project Infrastructure

- **No remote git configured** — local-only. If the machine dies, everything's gone.
- **`superposition.db` in `.gitignore`** but there's no seed script or migration system. Deleting the DB loses all test data. Need a `seed.py` or fixtures.
- **`pyproject.toml` pins `pydantic-settings`** but never uses it. Could be removed.
- **No CI config** (no `.github/workflows/`). Tests run manually.
- **No `Makefile` or script shortcuts** for common commands (`uv run python main.py`, `uv run pytest`, `uv run godot --headless`).
- **`.venv/` is inside the project tree** — not an issue per se but prevents `find` from being clean.

---

## Feature Gaps (Beyond Phase 2)

From `todo.md`:

1. **Agent scheduler and queue system** — the whole execution pipeline: agent selects task → approval gate → spawn process → capture run → log artifact. This is the core value prop of Superposition.
2. **Approval workflow with risk/urgency/priority vectors** — requires a state machine (pending → approved → rejected), agent identity, capability checks.
3. **Activity timeline view** — feed of all events across lanes.
4. **Automation playlists** — reusable sequences of tasks/cells.
5. **Calendar hooks** — schedule tasks in time.
6. **Full-text search** across artifacts, messages, cell outputs, logs.

Most of these need a lot more design work before implementation.