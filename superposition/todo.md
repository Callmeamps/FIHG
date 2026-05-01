# Superposition — Implementation Tasks

## Phase 1: Python Core + SQLite Foundation
- [x] Set up Python project structure (uv, FastAPI, SQLAlchemy, aiosqlite)
- [x] Define and apply SQLite schema (projects, tasks, artifacts, etc.)
- [x] Build core service with healthcheck endpoint and DB connection
- [x] Verify database connectivity and table creation
- [x] Add WebSocket event streaming (terminal output delivery)
- [x] Write simple tests for core models and API

## Phase 2: Terminal + Chatbooks
- [x] Implement PTY-based terminal runtime (Unix support)
- [x] Build terminal panel UI in Godot (TerminalPanel.tscn)
- [x] Create Chatbook surface (Chatbook.tscn) with message threading
- [x] Establish Godot ↔ Python API contract (HTTP/WebSocket)
- [x] Add cell execution support (shell/code cells)
- [x] Implement artifact linking from chat outputs
- [x] Enable task creation from messages/cells
- [ ] Design agent scheduler and queue system
- [ ] Implement approval workflow with risk/urgency/priority vectors
- [ ] Add agent execution permissions model
- [ ] Build agent queue UI component
- [ ] Integrate approvals into dashboard
- [ ] Test end-to-end agent run with approval gate

## Phase 4: Polish + Automation
- [ ] Build activity timeline view
- [ ] Add automation playlists support
- [ ] Implement calendar hooks (basic)
- [ ] Enhance search (across artifacts, logs, chat)
- [ ] Layout persistence for lanes
- [ ] Basic performance testing and optimization

## Cleanup Complete (2026-05-01)
### Frontend — completed
- [x] project.godot: Remove [dotnet] section + Jolt Physics
- [x] main.gd: TerminalPanel as child of TerminalDock, WS reconnect, Projects button wired
- [x] All scripts: Use API_BASE constant, error handling on all HTTP/JSON calls
- [x] terminal_panel.gd: Remove polling after write, rely on WS
- [x] dashboard.gd: Minimal health check display
- [x] projects_view: New scene for Projects nav button

### Backend — completed
- [x] _run_cell(): async subprocess (asyncio.create_subprocess_exec) + dispatch dict
- [x] datetime.utcnow() → datetime.now(UTC) everywhere
- [x] terminal_runtime from app.state (test isolation)
- [x] Cell execution creates Run record (provenance model)
- [x] Missing endpoints: GET /tasks, GET /chatbooks/{id}, DELETE/PUT chatbooks/artifacts/cells
- [x] Artifact create validates project exists
- [x] All 33 tests pass (18 original + 15 new)

### Remaining (see bd issues)
- [ ] Add auth tokens and CORS middleware (bd: Projects-grp, P1)
- [x] source_ref in Artifact unvalidated (bd: Projects-iam, P2) — Pydantic + CheckConstraint
- [x] TerminalRuntime uses asyncio.get_event_loop() in __init__ (bd: Projects-riq, P2) — fixed
- [ ] No CI (bd: Projects-vp1, P2)
- [x] No seed script/fixtures (bd: Projects-5ik, P2) — scripts/seed.py
- [ ] get_session fragile commit pattern (bd: Projects-8w6, P3)
- [ ] test_models.py uses AsyncSessionLocal directly (bd: Projects-ilq, P3)
- [ ] No Makefile shortcuts (bd: Projects-1vq, P3)

## Infrastructure
- [x] Set up Godot project structure (scenes, UI components)
- [x] Establish Godot ↔ Python API contract (HTTP/WebSocket)
- [x] Remove Docker Compose for local dev (Python + Postgres)
- [x] Configure development environment scripts

## Ubiquitous Language Refactor

Standardize domain terminology per `UBIQUITOUS_LANGUAGE.md`. Terms: **Lane** (not workspace/stream/thread for parallel context), **Spine** (not runtime/engine for execution layer), **Artifact** (not asset/attachment), **Chatbook** (not notebook/chat view), **Capability mask** (not permission set).

### Commit 1: Fix Task.runs model bug — add missing relationship
- [x] Add `runs = relationship("Run", back_populates="task")` to `Task` model
- [x] Verify `pytest` passes (tests currently fail on this)

### Commit 2: Fix "workspace/lane" language in README + todo
- [x] README: "production workspace" → "production environment" (app descriptor, not a Lane)
- [x] README: Remove "Workspace" from lane context references
- [x] todo.md: "Layout persistence for lanes/workspaces" → "Layout persistence for lanes"

### Commit 3: Fix "workspace/stream/thread" language in PRD
- [x] PRD: "Workspace / lane" section header → "Lane"
- [x] PRD: "A working context for one stream of effort" → "A working context for one effort"
- [x] PRD: "work on multiple threads at once" → "work on multiple lanes at once"
- [x] PRD: "multiple active workstreams" → "multiple active lanes"
- [x] PRD: "fast switching between workstreams" → "fast switching between lanes"
- [x] PRD: "stream of effort" → "lane"
- [x] PRD: "threaded messages" → "messages" (clarify it's message nesting not parallel work)
- [x] PRD: "client work" line item (ambiguous term but this is actual client work, not "Client" as UB term — leave as is)

### Commit 4: Fix "workspace/lane/stream/thread" language in design doc
- [x] Design doc: "may have a lane/workspace association" → "may have a lane association"
- [x] Design doc: "Workspace / lane" section header → "Lane"
- [x] Design doc: "stream stdout/stderr/events" → "relay stdout/stderr/events" (stream is a technical term here, keep as-is — clarify: this is stdout stream, not a Lane. Leave.)
- [x] Design doc: "WebSocket: UI live stream" → keep (technical term, not domain ambiguity)
- [x] Design doc: "GET /lanes/{id}" → keep (already correct)
- [x] Design doc: "Workspace / lane" → "Lane"
- [x] Design doc: "Each lane stores" → already correct
- [x] Design doc: "LaneSwitcher.tscn" → already correct
- [x] Design doc: "lane model" → already correct

### Commit 5: Remove obsolete DB file
- [x] `git rm -f superposition.db` (SQLite file is generated, not tracked — verify .gitignore)