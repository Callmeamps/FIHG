# Superposition — Product Requirements Document (PRD)

## 1. Product summary

**Superposition** is a local-first, personal production OS for a single user. It merges:
- notebook-style chat
- terminal execution
- project and task management
- agent coordination
- dashboard-based context switching

The core goal is simple: reduce the friction of working across too many apps, too many windows, and too many context switches.

Working product language:
- **Chatbooks** for chat + notebook workflows
- **Lane** for parallel contexts
- **Projects** and **tasks** for structured work
- **Artifacts** for persistent files and file chunks
- **Agents** for scheduled or delegated workflows

## 2. Problem statement

Current workflow is spread across multiple apps and devices:
- chat and planning in one place
- terminal work in another
- task tracking somewhere else
- notes, snippets, and files elsewhere

That split makes it hard to:
- keep context together
- work on multiple lanes at once
- turn notes or messages into action
- keep long-running work visible
- use agents without losing control

## 3. Product vision

Build a single local workspace where a developer can:
- open a project
- chat with the system
- run terminal commands
- track tasks
- attach artifacts
- coordinate agents
- switch between parallel lanes quickly

The system should feel like a command center, not a generic app suite.

## 4. Product principles

1. **Execution is real.** No fake terminal or simulated runtime.
2. **Graph is truth.** Structure lives in the graph, not the UI.
3. **UI is projection.** Godot renders state; it does not own it.
4. **Local-first.** Core work happens locally first, with sync later if needed.
5. **Simple first.** v1 should be narrow and useful.
6. **Human controlled.** Agents can act, but permissions and approval gates matter.
7. **Parallel by design.** The system must support multiple active lanes.
8. **KISS.** Avoid giant abstraction layers that do not help the solo user.

## 5. Target user

Primary user:
- one developer building software, researching, and managing tasks in parallel

Future user:
- a small team or agency workflow, but that is not the initial target

## 6. Product goals

### Primary goals
- unify chat, terminal, and task/project management in one place
- make fast switching between lanes easy
- support real execution, not mocked workflows
- support agent-assisted workflows with permissions
- keep work visible and persistent

### Secondary goals
- make the app usable as a daily driver
- allow the system to grow without rewriting the core
- keep the architecture friendly to future cloud sync

## 7. Non-goals for v1

- browser integration
- proprietary document support
- WYSIWYG editing
- animation editor
- full graph visualization as a first-class product surface
- heavy multi-user collaboration
- distributed cluster orchestration
- fully autonomous agents with no user control
- broad plugin marketplace
- replacing every productivity app

## 8. Core concepts

### Project
Top-level container for meaningful work. Projects contain tasks and artifacts.

### Task
A unit of work with status, priority, urgency, risk, links, and ownership.

### Artifact
Persistent data such as:
- files
- code snippets
- file chunks
- generated outputs
- notes bound to work items

### Process
A real running execution unit managed by the runtime spine.

### Agent
A workflow actor that can run scheduled or permissioned actions.

### Lane
A working context for one effort, with its own visible layout and active items.

### Chatbook
A notebook-like chat surface where messages, cells, outputs, and linked notes live together.

## 9. V1 feature set

### 9.1 Chatbooks
Chat + notebook hybrid. Supports:
- messages (with reply nesting)
- editable cells
- shell/code execution cells
- outputs linked back into the workspace
- conversion from message or cell into task/project items

### 9.2 Terminal emulator
A real terminal pane with persistent sessions, tied to the current project or lane.

### 9.3 Project management
Basic project and task control:
- create project
- create task
- set status
- link artifacts
- assign agents
- move between lanes

### 9.4 Agent coordination
A lightweight workflow queue for:
- scheduled runs
- follow-ups
- reminders
- task execution
- approval-gated actions

### 9.5 Dashboard
The default overview screen:
- active projects
- running terminals
- queued agents
- pending approvals
- recent artifacts
- recent activity

## 10. Workflow model

### Default entry path
- If projects exist, open the dashboard.
- If no project is active, open Chatbooks.

### Core flow
1. user opens a lane or project
2. user chats, plans, or runs commands
3. notes/cells/messages can be promoted to tasks
4. agents can work within permissions
5. outputs become artifacts
6. dashboard shows state and pending approvals

### Parallel work
The product should support multiple lanes at once:
- client work
- research
- implementation
- outreach / ops
- side experiments

Fast switching is a key value.

## 11. Approval and autonomy model

Agents do not get blanket authority.

Use a vector-based decision gate:
- **risk**
- **urgency**
- **priority**

Rules:
- low/medium mix can wait for user approval with a timeout
- high-risk combinations require explicit user approval
- user can pause tasks or projects
- agents can be permanent workflows, temporary workers, or scheduled helpers

## 12. Success criteria

For v1, the product is successful if the user can:
- keep multiple lanes open without losing context
- move from chat to terminal to task without app switching
- turn a thought into a task fast
- run useful agent workflows with clear control
- use the system daily without feeling forced into a giant platform

## 13. Product risks

- scope creep
- overbuilding agent autonomy
- making the UI too fancy before the workflow is solid
- letting Godot absorb backend logic
- trying to ship browser/docs support too early
- building graph tooling before the daily workflow exists

## 14. Milestone plan

### Phase 1
- Python core service
- Postgres schema
- basic project/task/artifact model
- terminal sessions
- dashboard shell

### Phase 2
- Chatbooks
- task creation from messages/cells
- agent queue
- approval flows
- lane switching

### Phase 3
- activity timeline
- automation playlists
- calendar hooks
- richer logs and search

### Later
- browser
- documents
- WYSIWYG editor
- artifact generation
- proprietary formats
- animation editor

## 15. Design constraints

- UI should stay modular
- core runtime must be real
- state must live outside the UI layer
- fast local performance matters
- the system must remain usable on weaker hardware

## 16. Open questions

- exact name: Superposition vs sub-brand for Chatbooks
- final home layout density
- how much agent scheduling is exposed directly in v1
- whether timeline comes before calendar
- how much visual graph access is worth shipping early

## 17. Definition of done for v1

v1 is done when the user can:
- open the app and see the right lane
- chat in a notebook-like surface
- run terminal work in the same workspace
- track projects and tasks
- attach artifacts to work
- queue and approve agent actions
- keep work flowing without juggling six apps

## 18. Reference notes

Implementation choices in the companion design doc are grounded in current official documentation for:
- Godot UI structure
- Python subprocess handling
- FastAPI live APIs
- SQLite JSON1 extension for flexible metadata, full-text search in v2
