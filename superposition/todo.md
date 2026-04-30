# Superposition — Implementation Tasks

## Phase 1: Python Core + Postgres Foundation
- [x] Set up Python project structure (uv, FastAPI, SQLAlchemy, psycopg)
- [x] Define and apply Postgres schema (projects, tasks, artifacts, etc.)
- [x] Build core service with healthcheck endpoint and DB connection
- [ ] Verify database connectivity and table creation (SQLite)
- [x] Add basic event streaming (WebSocket + LISTEN/NOTIFY plan)
- [x] Write simple tests for core models and API

## Phase 2: Terminal + Chatbooks
- [ ] Implement PTY-based terminal runtime (Unix support)
- [ ] Build terminal panel UI in Godot (TerminalPanel.tscn)
- [ ] Create Chatbook surface (Chatbook.tscn) with message threading
- [ ] Add cell execution support (shell/code cells)
- [ ] Implement artifact linking from chat outputs
- [ ] Enable task creation from messages/cells

## Phase 3: Agents + Approvals
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
- [ ] Layout persistence for lanes/workspaces
- [ ] Basic performance testing and optimization

## Infrastructure
- [ ] Set up Godot project structure (scenes, UI components)
- [ ] Establish Godot ↔ Python API contract (HTTP/WebSocket)
- [ ] Add Docker Compose for local dev (Python + Postgres)
- [ ] Configure development environment scripts
