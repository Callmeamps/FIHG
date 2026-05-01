# Ubiquitous Language

## Workspace / context

| Term | Definition | Aliases to avoid |
|------|------------|-----------------|
| **Lane** | A parallel working context with its own layout, active project, open chats, terminal sessions, and agent state | Workspace, stream, thread, session |
| **Dashboard** | Default overview screen showing active projects, running terminals, queued agents, pending approvals, and recent activity | Home, overview, workspace view |

## Structured work

| Term | Definition | Aliases to avoid |
|------|------------|-----------------|
| **Project** | Top-level container for meaningful work, containing tasks, artifacts, runs, and optionally a lane association | Workspace, folder, bucket |
| **Task** | A unit of actionable work with status, priority, urgency, risk, ownership, and optional due date | Issue, todo, item, ticket |
| **Artifact** | Persistent data bound to a project or task — files, snippets, chunks, generated outputs, notes | Asset, attachment, document |
| **Run** | A single execution event or job attempt tied to a process and optionally an agent | Execution, attempt, invocation |

## Execution

| Term | Definition | Aliases to avoid |
|------|------------|-----------------|
| **Process** | A real OS-level execution instance (subprocess or PTY) managed by the runtime spine | Job, thread, session |
| **Spine** | The execution layer that spawns processes, streams events, tracks lifecycle, and routes agent jobs — it does not own UI or business logic | Runtime, engine, backend, core |
| **Event** | A live notification emitted by the spine to the UI via WebSocket | Message, signal, notification |

## Agents & control

| Term | Definition | Aliases to avoid |
|------|------------|-----------------|
| **Agent** | A scheduled or permissioned workflow actor that operates within a scope | Bot, worker, automation |
| **Approval** | A user decision gate blocking an agent action until explicitly confirmed | Gate, accept, confirm, authorize |
| **Capability mask** | The explicit set of permissions granted to an agent (what it can do and where) | Permission set, scope mask, ACL |

## Chat & composition

| Term | Definition | Aliases to avoid |
|------|------------|-----------------|
| **Chatbook** | A notebook-like chat surface with threaded messages, editable code/shell cells, and outputs linked to the workspace | Notebook, chat view, message board |
| **Cell** | An executable block within a Chatbook — can be shell command or code snippet | Block, snippet, input |

## Relationships

- A **Project** has many **Tasks**, **Artifacts**, and **Runs**
- A **Task** belongs to exactly one **Project**
- An **Artifact** belongs to exactly one **Project** and optionally one **Task**
- A **Process** is tied to a **Project** and optionally a **Task** or **Lane**
- A **Run** belongs to exactly one **Process**, one **Project**, and optionally one **Agent** (actor)
- An **Agent** is assigned zero or more **Tasks** and may spawn **Runs**
- A **Lane** has one active **Project** and stores layout/panel state
- **Approvals** gate **Agent** actions based on a risk-urgency-priority vector

## Example dialogue

> **Dev:** "When I open a **Lane**, should I see the **Dashboard** or jump straight to the active **Project**?"
>
> **Domain expert:** "If the **Lane** has an active **Project**, show that **Project**'s **Tasks** and **Chatbook**. The **Dashboard** is the fallback when nothing is active."
>
> **Dev:** "And if I type in a **Chatbook Cell** and run it — does that spawn a **Process**?"
>
> **Domain expert:** "Yes. The **Spine** starts a **Process** for the shell or code. Its output becomes an **Artifact** that you can link back to the **Task** you're working on."
>
> **Dev:** "What if an **Agent** wants to run something risky? Does it just execute?"
>
> **Domain expert:** "No — the **Capability mask** says what it *can* do, but the **Approval** gate blocks high-risk actions. We check risk + urgency + priority. If too risky, the **Agent** pauses and the **Dashboard** pins a pending **Approval** for you."

## Flagged ambiguities

- **"Run" vs "Process"** — These were used interchangeably in early conversation. A **Process** is the OS instance; a **Run** is the *record* of execution. One Process can have many Runs.
- **"Core" vs "Spine"** — "Core" was used to mean both the Python backend service and the execution layer. The **spine** is the execution-and-event layer *inside* the core. The core is the whole Python service (API + spine + data).
- **"Workspace"** — Used to mean both the whole application ("production workspace") and a single parallel context. Replaced by **Lane** for the latter.
- **"Job" / "Worker" / "Bot"** — All used for agents. Standardize on **Agent** as the actor, **Run** as the single execution record.