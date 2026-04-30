# Superposition — Design Document

## 1. System summary

Superposition is a local-first workflow engine built around a real execution core and a Godot UI shell.

The system follows three strict layers:

- **Graph**: source of structure and meaning
- **Runtime spine**: source of execution and state change
- **UI**: projection only

The app is not a fake IDE, not a simulated shell, and not a database UI. It is a production workspace for a single user who needs chat, terminal, tasks, and agent coordination in one place.

## 2. Stack choice

### UI
**Godot** is the front-end shell.

Why it fits:
- cross-platform
- fast enough for a smooth workspace shell
- familiar to the builder
- strong Control / Container / Viewport UI primitives

Godot docs describe `Control` as the UI base class and explain that input is propagated through viewports. `Viewport` is the rendering surface, and `SubViewportContainer` can display a viewport inside a control surface. This makes Godot suitable for dock-like panels, embedded surfaces, and workspace projections. [1]

### Core runtime
**Python** is the backend service.

Why:
- fastest path to a working prototype
- easy process orchestration
- easy API work
- strong async tooling
- simple integration with the rest of the stack

FastAPI is a strong fit for the local core because it is a Python web framework for APIs, includes WebSocket support, and generates OpenAPI metadata automatically. [2]

### Data layer
**Postgres** is the primary database.

Why:
- relational truth for projects, tasks, agents, runs, and permissions
- JSONB for flexible metadata
- full-text search for artifacts, logs, and chat content
- LISTEN/NOTIFY for low-friction inter-process events
- future sync and multi-process access are easier than with a file-only store

PostgreSQL documentation recommends `jsonb` for most applications when storing JSON data, because it is faster to process and supports indexing. It also has built-in full-text search and LISTEN/NOTIFY for asynchronous notification between sessions. [3][4][5]

### Artifact storage
Use local files for large or binary artifacts, with database rows storing:
- path
- type
- checksum
- ownership links
- metadata

## 3. Core architecture

```text
Godot UI
  └─ talks to ─> Python Core API
                   ├─ Postgres
                   ├─ Artifact files
                   ├─ Shell / PTY runtime
                   ├─ Agent scheduler
                   └─ Event stream
```

The Python core is the authoritative execution service. Godot remains a shell that renders state and sends user intent.

## 4. Core primitives

### 4.1 Project
Top-level work container.

Fields:
- id
- title
- description
- status
- priority
- urgency
- risk
- created_at
- updated_at

Relationships:
- has many tasks
- has many artifacts
- has many runs
- may have a lane/workspace association

### 4.2 Task
A unit of actionable work.

Fields:
- id
- project_id
- title
- status
- priority
- urgency
- risk
- due_at
- assigned_agent_id
- approval_state
- created_from_ref

### 4.3 Artifact
A persistent work object.

Fields:
- id
- project_id
- task_id
- kind
- title
- content_text or file_path
- hash
- source_ref
- tags

Kinds:
- file
- snippet
- chunk
- output
- patch
- note

### 4.4 Agent
A scheduled or permissioned workflow actor.

Fields:
- id
- name
- mode
- schedule
- capability_mask
- parent_scope
- status

Modes:
- fulltime workflow daemon
- part-time worker
- temporary task worker

### 4.5 Process
A real runtime execution instance.

Fields:
- id
- type
- command
- pid
- status
- tty/session info
- project_id
- task_id
- lane_id

### 4.6 Run
A single execution event or job attempt.

Fields:
- id
- process_id
- actor_id
- input
- output
- status
- started_at
- finished_at

### 4.7 Event / log
Scratch log entries only for v1.

Used for:
- debugging
- recent replay
- audit trail
- status updates

Not used as the only source of truth for v1.

### 4.8 Workspace / lane
A layout and context container.

Fields:
- id
- title
- active_project_id
- layout_state
- pinned_panels
- recent_items

## 5. Runtime spine

The runtime spine manages real execution and stateful work.

Responsibilities:
- spawn processes
- attach to terminal sessions
- stream stdout/stderr/events
- track process lifecycle
- route agent jobs
- accept approval decisions
- emit change events to the database and UI

The runtime spine does not:
- define layout
- own user-facing state
- replace the graph
- simulate processes

### 5.1 Terminal implementation
Python has direct support for subprocess management through `asyncio.create_subprocess_shell()` and related APIs. [6]

For terminal-style interaction, Python’s `pty` module can create and control pseudo-terminals, but the standard library docs note it is Unix-only and platform dependent. [7]

Design implication:
- build a PTY-based backend for Unix-like systems
- provide a platform abstraction for Windows later if needed
- keep terminal semantics behind one runtime interface

### 5.2 Eventing
For live updates, use one of:
- FastAPI WebSockets between UI and core
- Postgres LISTEN/NOTIFY for internal process fanout
- both together

FastAPI supports WebSockets directly. [8]
Postgres LISTEN/NOTIFY provides simple interprocess notification among sessions in the same database. [4][5]

Recommended split:
- WebSocket: UI live stream
- LISTEN/NOTIFY: backend process wakeups and lightweight event propagation

## 6. API contract

The main API between UI and core should stay small.

### Suggested endpoints
- `POST /projects`
- `POST /tasks`
- `POST /artifacts`
- `POST /agents`
- `POST /processes`
- `POST /runs`
- `POST /approvals`
- `GET /dashboard`
- `GET /lanes/{id}`
- `POST /chatbooks/{id}/messages`
- `POST /chatbooks/{id}/cells`
- `WS /events`

### Core operations
- spawn
- invoke
- stream
- snapshot
- link
- approve
- pause
- resume
- cancel

## 7. Approval system

Use a 3-vector decision model:
- risk
- urgency
- priority

Routing logic:
- low/low/low can auto-continue
- mixed low-mid can wait for a user window
- high combinations pause and require explicit approval
- user can set project-level policies

This keeps autonomy useful without turning the system into an uncontrollable agent farm.

## 8. Agent coordination model

Agents operate inside scopes.

Rules:
- an agent cannot change ancestor scopes
- permissions are explicit
- generated subagents inherit only the allowed capability set
- permanent agents can run schedules or sequences
- temporary agents are created for one task or sequence

Common workflows:
- lead follow-up
- bug triage
- research summary
- patch proposal
- repo watcher
- notification bot
- deadline reminder

## 9. UI design

### 9.1 Main layout
The working layout is:

- **left rail**: navigation
- **center viewport**: primary content
- **bottom terminal/log dock**: live execution surface

This is the dashboard default.

### 9.2 Why this layout
It matches the actual workflow:
- navigation on the left
- content in the middle
- execution at the bottom
- inspector or metadata on the right later if needed

### 9.3 Panels
Initial panels:
- Projects
- Tasks
- Chatbooks
- Terminal
- Agents
- Activity
- Artifacts

### 9.4 Workspace / lane model
Each lane stores:
- active project
- open chatbook
- active terminal sessions
- pinned task view
- agent queue state
- saved layout

This is the main parallel-work feature.

### 9.5 Godot scene guidance
Use `Control`-based UI only for the app shell. Containers should manage layout, not manual positioning everywhere. Viewport and SubViewportContainer are useful for embedded panels or future specialized content surfaces. [1]

Recommended pattern:
- `Main.tscn`
- `Dashboard.tscn`
- `Chatbook.tscn`
- `TerminalPanel.tscn`
- `ProjectBoard.tscn`
- `Inspector.tscn`
- `LaneSwitcher.tscn`

## 10. Data model strategy

### Recommended storage split
**Postgres**
- projects
- tasks
- artifacts metadata
- agents
- processes
- runs
- approvals
- logs
- layouts
- lanes

**Filesystem**
- large artifact bodies
- raw files
- binary blobs
- generated outputs

### Why JSONB
Use JSONB for flexible metadata such as:
- artifact tags
- terminal session settings
- agent configuration
- layout state
- task extras

Postgres recommends JSONB for most applications because it is faster to process and indexable. [3]

### Why full-text search
Use full-text search for:
- notes
- chatbook content
- logs
- artifact text
- task descriptions

This is a good fit for the “search my whole workspace” requirement. [5]

## 11. Activity logging

For v1, logging is scratch logging:
- store recent process output
- keep task actions
- keep agent actions
- keep user approvals
- keep simple replay data

Do not make logs the only canonical store yet.

Later, logs can be expanded into more structured event history.

## 12. Milestone build order

### Milestone 1
- Python service
- Postgres schema
- project/task/artifact tables
- dashboard shell
- lane model
- basic fast navigation

### Milestone 2
- terminal runtime
- chatbook surface
- artifact linking
- task creation from chat
- approval workflow

### Milestone 3
- agent queue
- scheduled workflows
- activity log view
- simple timeline

### Milestone 4
- automation playlists
- calendar hooks
- better search
- polished layout behavior

## 13. Risks

### Scope creep
The system can become too large too fast. Keep browser/docs/WYSIWYG out of the first ship.

### UI overreach
The app should not become a heavy visual toy before the daily workflow is solid.

### Backend leakage into UI
Godot should not own business logic.

### Platform friction
Terminal handling differs by platform. The Unix PTY path is straightforward, but Windows needs a separate plan. [7]

### Autonomy risk
Agents need policy gates or they become noisy and hard to debug.

## 14. Open questions

- final working name for Chatbooks
- how much automation is exposed in v1
- whether timeline comes before calendar
- whether a simple graph view is worth shipping early
- how much of the agent scheduler should be visible in the first UI

## 15. Recommended implementation plan

1. Build the Postgres schema.
2. Build the Python FastAPI core.
3. Add event streaming.
4. Add the Godot shell with left rail / viewport / terminal dock.
5. Add projects, tasks, and artifacts.
6. Add Chatbooks.
7. Add agents and approvals.
8. Add timelines and automation playlists.

## 16. References

[1] Godot Engine documentation: `Control`, `Viewport`, `SubViewportContainer`  
[2] FastAPI official documentation  
[3] PostgreSQL official documentation: JSON types / JSONB  
[4] PostgreSQL official documentation: LISTEN / NOTIFY  
[5] PostgreSQL official documentation: Full Text Search  
[6] Python official documentation: `asyncio.subprocess`  
[7] Python official documentation: `pty`  
[8] FastAPI official documentation: WebSockets
