# Superposition — Implementation Tasks

## Phase 1: Python Core + Postgres Foundation
- [x] Set up Python project structure (uv, FastAPI, SQLAlchemy, psycopg)
- [x] Define and apply Postgres schema (projects, tasks, artifacts, etc.)
- [x] Build core service with healthcheck endpoint and DB connection
- [x] Verify database connectivity and table creation (SQLite)
- [x] Add basic event streaming (WebSocket + LISTEN/NOTIFY plan)
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
- [ ] Enhance search (full-text across artifacts, logs, chat)
- [ ] Layout persistence for lanes
- [ ] Basic performance testing and optimization

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