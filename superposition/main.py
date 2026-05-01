import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from superposition.db import engine, Base, get_session
from superposition.terminal import TerminalRuntime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

import superposition.models  # noqa: F401
from superposition.models import Project, Task, Artifact, Agent, Process, Run, Lane, Chatbook, Message, Cell, Approval


# --- Pydantic schemas -------------------------------------------------------

class CreateProject(BaseModel):
    title: str
    description: Optional[str] = None

class UpdateProject(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class CreateTask(BaseModel):
    project_id: str
    title: str
    status: Optional[str] = "todo"

class UpdateTask(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None

class CreateChatbook(BaseModel):
    project_id: str
    title: Optional[str] = "New Chat"

class UpdateChatbook(BaseModel):
    title: Optional[str] = None

class SendMessage(BaseModel):
    role: str = "user"
    content: str
    parent_id: Optional[str] = None

class SpawnTerminal(BaseModel):
    command: Optional[str] = "/bin/bash"

class WriteTerminal(BaseModel):
    data: str


class CreateCell(BaseModel):
    chatbook_id: str
    language: str = "shell"
    source: str

class UpdateCell(BaseModel):
    language: Optional[str] = None
    source: Optional[str] = None

class CreateArtifact(BaseModel):
    project_id: str
    task_id: Optional[str] = None
    kind: str = "text"
    title: str
    content_text: Optional[str] = None
    source_ref: Optional[str] = None
    tags: Optional[list[str]] = None

    @field_validator("source_ref")
    @classmethod
    def source_ref_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not (v.startswith("cell:") or v.startswith("message:")):
            raise ValueError('source_ref must start with "cell:" or "message:"')
        return v

class UpdateArtifact(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    tags: Optional[list[str]] = None

class CreateLane(BaseModel):
    title: str
    active_project_id: Optional[str] = None


class UpdateLane(BaseModel):
    title: Optional[str] = None
    active_project_id: Optional[str] = None
    layout_state: Optional[dict] = None
    pinned_panels: Optional[list] = None
    recent_items: Optional[list] = None


class CreateAgent(BaseModel):
    name: str
    mode: str
    schedule: Optional[dict] = None
    capability_mask: Optional[dict] = None
    parent_scope: Optional[str] = None
    status: str = "idle"


class UpdateAgent(BaseModel):
    name: Optional[str] = None
    mode: Optional[str] = None
    schedule: Optional[dict] = None
    capability_mask: Optional[dict] = None
    parent_scope: Optional[str] = None
    status: Optional[str] = None


class CreateRun(BaseModel):
    project_id: str
    process_id: str
    actor_id: Optional[str] = None
    cell_id: Optional[str] = None
    status: str = "running"
    input: Optional[dict] = None
    output: Optional[str] = None
    started_at: Optional[str] = None  # ISO8601 string


class UpdateRun(BaseModel):
    status: Optional[str] = None
    output: Optional[str] = None
    finished_at: Optional[str] = None  # ISO8601 string


class CreateProcess(BaseModel):
    type: str
    command: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    lane_id: Optional[str] = None
    status: str = "starting"


class UpdateProcess(BaseModel):
    type: Optional[str] = None
    command: Optional[str] = None
    pid: Optional[int] = None
    status: Optional[str] = None
    tty_info: Optional[dict] = None


class CreateApproval(BaseModel):
    agent_id: str
    action_type: str
    action_payload: Optional[dict] = None
    risk: int = 1
    urgency: int = 1
    priority: int = 1
    project_id: Optional[str] = None

    @field_validator("risk", "urgency", "priority")
    @classmethod
    def score_range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Score must be between 1 and 5")
        return v


class RespondApproval(BaseModel):
    decision: str  # "approved" or "denied"
    reason: Optional[str] = None


class ExecuteCell(BaseModel):
    language: str = "shell"
    source: str


# --- Auth & rate limiting ---------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=[os.environ.get("RATE_LIMIT", "60/min")])


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Validate X-API-Key against the API_KEY env var. Open when API_KEY is unset."""
    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        return "open"  # auth disabled when no key is configured
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    if x_api_key != api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


# --- Connection manager ----------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


# --- App setup --------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.ws_manager = ConnectionManager()
    app.state.terminal_runtime = TerminalRuntime()

    yield

    # Close all PTY sessions
    rt = app.state.terminal_runtime
    for sid in list(rt._sessions.keys()):
        try:
            await rt.close(sid)
        except Exception:
            pass

    await engine.dispose()

app = FastAPI(title="Superposition", version="0.1.0", lifespan=lifespan)


# --- Helpers ----------------------------------------------------------------

def get_manager() -> ConnectionManager:
    return app.state.ws_manager

def get_terminal_runtime() -> TerminalRuntime:
    return app.state.terminal_runtime


# --- Health ----------------------------------------------------------------

@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# --- Dashboard -------------------------------------------------------------

@app.get("/dashboard")
async def get_dashboard(
    _auth: str = Depends(verify_api_key),
    rt: TerminalRuntime = Depends(get_terminal_runtime),
    session: AsyncSession = Depends(get_session)
):
    """Aggregate dashboard data: active projects, running terminals, queued agents, recent artifacts."""
    # Active projects (5 most recent)
    proj_result = await session.execute(
        select(Project).order_by(Project.created_at.desc()).limit(5)
    )
    projects = [{"id": p.id, "title": p.title, "status": p.status}
                for p in proj_result.scalars().all()]

    # Running terminal sessions
    sessions = []
    for s in rt.sessions.values():
        sessions.append({"id": s.id, "command": s.command, "pid": s.pid, "status": s.status})

    # Queued agents
    agent_result = await session.execute(
        select(Agent).where(Agent.status.in_(["queued", "idle"])).limit(10)
    )
    agents = [{"id": a.id, "name": a.name, "status": a.status, "mode": a.mode}
              for a in agent_result.scalars().all()]

    # Recent artifacts (5 most recent)
    art_result = await session.execute(
        select(Artifact).order_by(Artifact.created_at.desc()).limit(5)
    )
    artifacts = [{"id": a.id, "title": a.title, "kind": a.kind, "project_id": a.project_id}
                 for a in art_result.scalars().all()]

    # Recent tasks
    task_result = await session.execute(
        select(Task).order_by(Task.created_at.desc()).limit(5)
    )
    tasks = [{"id": t.id, "title": t.title, "status": t.status, "project_id": t.project_id}
             for t in task_result.scalars().all()]

    return {
        "projects": projects,
        "running_terminals": sessions,
        "queued_agents": agents,
        "recent_artifacts": artifacts,
        "recent_tasks": tasks,
    }


# --- Projects --------------------------------------------------------------

@app.get("/projects")
async def list_projects(_auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return [{"id": p.id, "title": p.title, "status": p.status}
            for p in result.scalars().all()]

@app.post("/projects")
async def create_project(body: CreateProject, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    project = Project(title=body.title, description=body.description)
    session.add(project)
    await session.flush()
    return {"id": project.id, "title": project.title, "status": project.status}

@app.get("/projects/{project_id}")
async def get_project(project_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"id": project.id, "title": project.title, "description": project.description,
            "status": project.status, "created_at": project.created_at.isoformat() if project.created_at else None}

@app.put("/projects/{project_id}")
async def update_project(project_id: str, body: UpdateProject, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.title is not None:
        project.title = body.title
    if body.description is not None:
        project.description = body.description
    if body.status is not None:
        project.status = body.status
    await session.flush()
    return {"id": project.id, "title": project.title, "status": project.status}


# --- Tasks ------------------------------------------------------------------

@app.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Task).order_by(Task.created_at.desc())
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    if status:
        stmt = stmt.where(Task.status == status)
    result = await session.execute(stmt)
    return [{"id": t.id, "title": t.title, "status": t.status,
             "project_id": t.project_id, "priority": t.priority,
             "created_at": t.created_at.isoformat() if t.created_at else None}
            for t in result.scalars().all()]

@app.post("/tasks")
async def create_task(body: CreateTask, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    task = Task(project_id=body.project_id, title=body.title, status=body.status)
    session.add(task)
    await session.flush()
    return {"id": task.id, "title": task.title, "status": task.status}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task.id, "title": task.title, "status": task.status,
            "project_id": task.project_id}

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, body: UpdateTask, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.title is not None:
        task.title = body.title
    if body.status is not None:
        task.status = body.status
    await session.flush()
    return {"id": task.id, "title": task.title, "status": task.status}


# --- Chatbooks -------------------------------------------------------------

@app.get("/chatbooks")
async def list_chatbooks(project_id: Optional[str] = None, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    stmt = select(Chatbook).order_by(Chatbook.updated_at.desc())
    if project_id:
        stmt = stmt.where(Chatbook.project_id == project_id)
    result = await session.execute(stmt)
    return [{"id": cb.id, "title": cb.title, "project_id": cb.project_id,
             "created_at": cb.created_at.isoformat() if cb.created_at else None}
            for cb in result.scalars().all()]

@app.post("/chatbooks")
async def create_chatbook(body: CreateChatbook, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    cb = Chatbook(project_id=body.project_id, title=body.title)
    session.add(cb)
    await session.flush()
    return {"id": cb.id, "title": cb.title, "project_id": cb.project_id}

@app.get("/chatbooks/{chatbook_id}")
async def get_chatbook(chatbook_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    cb = await session.get(Chatbook, chatbook_id)
    if not cb:
        raise HTTPException(status_code=404, detail="Chatbook not found")
    return {"id": cb.id, "title": cb.title, "project_id": cb.project_id,
            "lane_id": cb.lane_id,
            "created_at": cb.created_at.isoformat() if cb.created_at else None,
            "updated_at": cb.updated_at.isoformat() if cb.updated_at else None}

@app.put("/chatbooks/{chatbook_id}")
async def update_chatbook(chatbook_id: str, body: UpdateChatbook, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    cb = await session.get(Chatbook, chatbook_id)
    if not cb:
        raise HTTPException(status_code=404, detail="Chatbook not found")
    if body.title is not None:
        cb.title = body.title
    await session.flush()
    return {"id": cb.id, "title": cb.title}

@app.delete("/chatbooks/{chatbook_id}")
async def delete_chatbook(chatbook_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    cb = await session.get(Chatbook, chatbook_id)
    if not cb:
        raise HTTPException(status_code=404, detail="Chatbook not found")
    await session.delete(cb)
    await session.flush()
    return {"status": "deleted"}

@app.get("/chatbooks/{chatbook_id}/messages")
async def list_messages(chatbook_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Message).where(Message.chatbook_id == chatbook_id).order_by(Message.created_at)
    )
    return [{"id": m.id, "role": m.role, "content": m.content, "parent_id": m.parent_id,
             "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in result.scalars().all()]

@app.post("/chatbooks/{chatbook_id}/messages")
async def send_message(chatbook_id: str, body: SendMessage, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    chatbook = await session.get(Chatbook, chatbook_id)
    if not chatbook:
        raise HTTPException(status_code=404, detail="Chatbook not found")
    msg = Message(chatbook_id=chatbook_id, role=body.role, content=body.content, parent_id=body.parent_id)
    session.add(msg)
    await session.flush()
    return {"id": msg.id, "role": msg.role, "content": msg.content}


# --- Lanes ------------------------------------------------------------------

@app.get("/lanes")
async def list_lanes(_auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Lane).order_by(Lane.created_at.desc()))
    return [{"id": l.id, "title": l.title, "active_project_id": l.active_project_id,
             "created_at": l.created_at.isoformat() if l.created_at else None}
            for l in result.scalars().all()]

@app.post("/lanes")
async def create_lane(body: CreateLane, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    if body.active_project_id:
        project = await session.get(Project, body.active_project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    lane = Lane(title=body.title, active_project_id=body.active_project_id)
    session.add(lane)
    await session.flush()
    return {"id": lane.id, "title": lane.title, "active_project_id": lane.active_project_id,
            "created_at": lane.created_at.isoformat() if lane.created_at else None}

@app.get("/lanes/{lane_id}")
async def get_lane(lane_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    lane = await session.get(Lane, lane_id)
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found")
    return {"id": lane.id, "title": lane.title, "active_project_id": lane.active_project_id,
            "layout_state": lane.layout_state, "pinned_panels": lane.pinned_panels,
            "recent_items": lane.recent_items,
            "created_at": lane.created_at.isoformat() if lane.created_at else None,
            "updated_at": lane.updated_at.isoformat() if lane.updated_at else None}

@app.put("/lanes/{lane_id}")
async def update_lane(lane_id: str, body: UpdateLane, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    lane = await session.get(Lane, lane_id)
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found")
    if body.active_project_id is not None:
        if body.active_project_id != "":
            project = await session.get(Project, body.active_project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
        lane.active_project_id = body.active_project_id if body.active_project_id != "" else None
    if body.title is not None:
        lane.title = body.title
    if body.layout_state is not None:
        lane.layout_state = body.layout_state
    if body.pinned_panels is not None:
        lane.pinned_panels = body.pinned_panels
    if body.recent_items is not None:
        lane.recent_items = body.recent_items
    await session.flush()
    return {"id": lane.id, "title": lane.title, "active_project_id": lane.active_project_id}

@app.delete("/lanes/{lane_id}")
async def delete_lane(lane_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    lane = await session.get(Lane, lane_id)
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found")
    await session.delete(lane)
    await session.flush()
    return {"status": "deleted"}


# --- Agents -----------------------------------------------------------------

@app.get("/agents")
async def list_agents(_auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Agent))
    return [{"id": a.id, "name": a.name, "mode": a.mode, "status": a.status,
             "parent_scope": a.parent_scope}
            for a in result.scalars().all()]

@app.post("/agents")
async def create_agent(body: CreateAgent, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    if body.parent_scope:
        parent = await session.get(Agent, body.parent_scope)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent agent not found")
    agent = Agent(
        name=body.name,
        mode=body.mode,
        schedule=body.schedule,
        capability_mask=body.capability_mask,
        parent_scope=body.parent_scope,
        status=body.status,
    )
    session.add(agent)
    await session.flush()
    return {"id": agent.id, "name": agent.name, "mode": agent.mode, "status": agent.status}

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"id": agent.id, "name": agent.name, "mode": agent.mode,
            "schedule": agent.schedule, "capability_mask": agent.capability_mask,
            "parent_scope": agent.parent_scope, "status": agent.status}

@app.put("/agents/{agent_id}")
async def update_agent(agent_id: str, body: UpdateAgent, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if body.name is not None:
        agent.name = body.name
    if body.mode is not None:
        agent.mode = body.mode
    if body.schedule is not None:
        agent.schedule = body.schedule
    if body.capability_mask is not None:
        agent.capability_mask = body.capability_mask
    if body.parent_scope is not None:
        if body.parent_scope != "":
            parent = await session.get(Agent, body.parent_scope)
            if not parent:
                raise HTTPException(status_code=404, detail="Parent agent not found")
        agent.parent_scope = body.parent_scope if body.parent_scope != "" else None
    if body.status is not None:
        agent.status = body.status
    await session.flush()
    return {"id": agent.id, "name": agent.name, "mode": agent.mode, "status": agent.status}

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.delete(agent)
    await session.flush()
    return {"status": "deleted"}


# --- Processes ------------------------------------------------------------

@app.get("/processes")
async def list_processes(
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    status: Optional[str] = None,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Process)
    if project_id:
        stmt = stmt.where(Process.project_id == project_id)
    if task_id:
        stmt = stmt.where(Process.task_id == task_id)
    if status:
        stmt = stmt.where(Process.status == status)
    result = await session.execute(stmt)
    return [{"id": p.id, "type": p.type, "command": p.command, "pid": p.pid,
             "status": p.status, "project_id": p.project_id, "task_id": p.task_id}
            for p in result.scalars().all()]

@app.post("/processes")
async def create_process(body: CreateProcess, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    if body.project_id:
        project = await session.get(Project, body.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    proc = Process(
        type=body.type,
        command=body.command,
        project_id=body.project_id,
        task_id=body.task_id,
        lane_id=body.lane_id,
        status=body.status,
    )
    session.add(proc)
    await session.flush()
    return {"id": proc.id, "type": proc.type, "command": proc.command, "status": proc.status}

@app.get("/processes/{process_id}")
async def get_process(process_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    proc = await session.get(Process, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process not found")
    return {"id": proc.id, "type": proc.type, "command": proc.command, "pid": proc.pid,
            "status": proc.status, "tty_info": proc.tty_info,
            "project_id": proc.project_id, "task_id": proc.task_id, "lane_id": proc.lane_id}

@app.put("/processes/{process_id}")
async def update_process(process_id: str, body: UpdateProcess, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    proc = await session.get(Process, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process not found")
    if body.type is not None:
        proc.type = body.type
    if body.command is not None:
        proc.command = body.command
    if body.pid is not None:
        proc.pid = body.pid
    if body.status is not None:
        proc.status = body.status
    if body.tty_info is not None:
        proc.tty_info = body.tty_info
    await session.flush()
    return {"id": proc.id, "type": proc.type, "status": proc.status}

@app.delete("/processes/{process_id}")
async def delete_process(process_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    proc = await session.get(Process, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process not found")
    await session.delete(proc)
    await session.flush()
    return {"status": "deleted"}


# --- Runs ------------------------------------------------------------------

@app.get("/runs")
async def list_runs(
    project_id: Optional[str] = None,
    process_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    status: Optional[str] = None,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Run).order_by(Run.started_at.desc())
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    if process_id:
        stmt = stmt.where(Run.process_id == process_id)
    if actor_id:
        stmt = stmt.where(Run.actor_id == actor_id)
    if status:
        stmt = stmt.where(Run.status == status)
    result = await session.execute(stmt)
    return [{"id": r.id, "project_id": r.project_id, "process_id": r.process_id,
             "actor_id": r.actor_id, "cell_id": r.cell_id, "status": r.status,
             "started_at": r.started_at.isoformat() if r.started_at else None}
            for r in result.scalars().all()]

@app.post("/runs")
async def create_run(body: CreateRun, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    proc = await session.get(Process, body.process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process not found")
    if body.actor_id:
        agent = await session.get(Agent, body.actor_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
    started = datetime.now(UTC)
    if body.started_at:
        started = datetime.fromisoformat(body.started_at.replace("Z", "+00:00"))
    run = Run(
        project_id=body.project_id,
        process_id=body.process_id,
        actor_id=body.actor_id,
        cell_id=body.cell_id,
        status=body.status,
        input=body.input,
        output=body.output,
        started_at=started,
    )
    session.add(run)
    await session.flush()
    return {"id": run.id, "project_id": run.project_id, "process_id": run.process_id,
            "status": run.status, "started_at": run.started_at.isoformat() if run.started_at else None}

@app.get("/runs/{run_id}")
async def get_run(run_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"id": run.id, "project_id": run.project_id, "process_id": run.process_id,
            "actor_id": run.actor_id, "cell_id": run.cell_id, "input": run.input,
            "output": run.output, "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None}

@app.put("/runs/{run_id}")
async def update_run(run_id: str, body: UpdateRun, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if body.status is not None:
        run.status = body.status
    if body.output is not None:
        run.output = body.output
    if body.finished_at is not None:
        run.finished_at = datetime.fromisoformat(body.finished_at.replace("Z", "+00:00"))
    await session.flush()
    return {"id": run.id, "status": run.status,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None}

@app.delete("/runs/{run_id}")
async def delete_run(run_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await session.delete(run)
    await session.flush()
    return {"status": "deleted"}


# --- Terminal sessions -----------------------------------------------------

@limiter.limit("10/min")
@app.post("/terminal/spawn")
async def terminal_spawn(request: Request, body: SpawnTerminal, _auth: str = Depends(verify_api_key), rt: TerminalRuntime = Depends(get_terminal_runtime)):
    sess = await rt.spawn(command=body.command or "/bin/bash")
    return {"session_id": sess.id, "pid": sess.pid, "status": sess.status}

@app.post("/terminal/{session_id}/write")
async def terminal_write(session_id: str, body: WriteTerminal, _auth: str = Depends(verify_api_key), rt: TerminalRuntime = Depends(get_terminal_runtime)):
    try:
        await rt.write(session_id, body.data)
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}

@app.post("/terminal/{session_id}/resize")
async def terminal_resize(session_id: str, cols: int = Query(80), rows: int = Query(24), _auth: str = Depends(verify_api_key), rt: TerminalRuntime = Depends(get_terminal_runtime)):
    try:
        await rt.resize(session_id, cols, rows)
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}

@app.post("/terminal/{session_id}/close")
async def terminal_close(session_id: str, _auth: str = Depends(verify_api_key), rt: TerminalRuntime = Depends(get_terminal_runtime)):
    await rt.close(session_id)
    return {"status": "closed"}

@app.get("/terminal/sessions")
async def list_terminal_sessions(_auth: str = Depends(verify_api_key), rt: TerminalRuntime = Depends(get_terminal_runtime)):
    return {"sessions": [{"id": s.id, "status": s.status, "pid": s.pid}
                         for s in rt.sessions.values()]}


# --- Artifacts --------------------------------------------------------------

@app.post("/artifacts")
async def create_artifact(body: CreateArtifact, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    artifact = Artifact(
        project_id=body.project_id,
        task_id=body.task_id,
        kind=body.kind,
        title=body.title,
        content_text=body.content_text,
        source_ref=body.source_ref,
        tags=body.tags,
    )
    session.add(artifact)
    await session.flush()
    return {"id": artifact.id, "title": artifact.title, "kind": artifact.kind,
            "source_ref": artifact.source_ref, "tags": artifact.tags,
            "task_id": artifact.task_id, "project_id": artifact.project_id}

@app.get("/artifacts")
async def list_artifacts(
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Artifact).order_by(Artifact.created_at.desc())
    if project_id:
        stmt = stmt.where(Artifact.project_id == project_id)
    if task_id:
        stmt = stmt.where(Artifact.task_id == task_id)
    result = await session.execute(stmt)
    return [{"id": a.id, "title": a.title, "kind": a.kind,
             "content_text": a.content_text, "source_ref": a.source_ref,
             "tags": a.tags, "project_id": a.project_id, "task_id": a.task_id}
            for a in result.scalars().all()]

@app.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"id": artifact.id, "title": artifact.title, "kind": artifact.kind,
            "content_text": artifact.content_text, "source_ref": artifact.source_ref,
            "tags": artifact.tags, "project_id": artifact.project_id, "task_id": artifact.task_id}

@app.put("/artifacts/{artifact_id}")
async def update_artifact(artifact_id: str, body: UpdateArtifact, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if body.title is not None:
        artifact.title = body.title
    if body.content_text is not None:
        artifact.content_text = body.content_text
    if body.tags is not None:
        artifact.tags = body.tags
    await session.flush()
    return {"id": artifact.id, "title": artifact.title, "tags": artifact.tags}

@app.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    await session.delete(artifact)
    await session.flush()
    return {"status": "deleted"}


# --- Approvals -------------------------------------------------------------

@app.get("/approvals")
async def list_approvals(
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Approval).order_by(Approval.created_at.desc())
    if status:
        stmt = stmt.where(Approval.status == status)
    if agent_id:
        stmt = stmt.where(Approval.agent_id == agent_id)
    result = await session.execute(stmt)
    return [{"id": a.id, "agent_id": a.agent_id, "action_type": a.action_type,
             "risk": a.risk, "urgency": a.urgency, "priority": a.priority,
             "status": a.status, "project_id": a.project_id,
             "created_at": a.created_at.isoformat() if a.created_at else None,
             "responded_at": a.responded_at.isoformat() if a.responded_at else None}
            for a in result.scalars().all()]

@app.post("/approvals")
async def create_approval(body: CreateApproval, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    agent = await session.get(Agent, body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if body.project_id:
        project = await session.get(Project, body.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    approval = Approval(
        agent_id=body.agent_id,
        action_type=body.action_type,
        action_payload=body.action_payload,
        risk=body.risk,
        urgency=body.urgency,
        priority=body.priority,
        project_id=body.project_id,
        status="pending",
    )
    session.add(approval)
    await session.flush()
    return {"id": approval.id, "agent_id": approval.agent_id, "action_type": approval.action_type,
            "risk": approval.risk, "urgency": approval.urgency, "priority": approval.priority,
            "status": approval.status, "project_id": approval.project_id,
            "created_at": approval.created_at.isoformat() if approval.created_at else None}

@app.get("/approvals/{approval_id}")
async def get_approval(approval_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    approval = await session.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"id": approval.id, "agent_id": approval.agent_id, "action_type": approval.action_type,
            "action_payload": approval.action_payload, "risk": approval.risk,
            "urgency": approval.urgency, "priority": approval.priority,
            "status": approval.status, "reason": approval.reason,
            "project_id": approval.project_id,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
            "responded_at": approval.responded_at.isoformat() if approval.responded_at else None}

@app.post("/approvals/{approval_id}/respond")
async def respond_approval(approval_id: str, body: RespondApproval, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    approval = await session.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail=f"Approval already {approval.status}")
    if body.decision not in ("approved", "denied"):
        raise HTTPException(status_code=422, detail="decision must be 'approved' or 'denied'")
    approval.status = body.decision
    approval.reason = body.reason
    approval.responded_at = datetime.now(UTC)
    await session.flush()
    return {"id": approval.id, "status": approval.status, "reason": approval.reason,
            "responded_at": approval.responded_at.isoformat() if approval.responded_at else None}


# --- Cell execution -------------------------------------------------------

# Dispatch table: language → (cmd, shell_arg) for asyncio subprocess
_CELL_RUNNERS = {
    "shell": (["/bin/bash", "-c"], None),
    "python": (["python3", "-c"], None),
}


async def _run_cell(source: str, language: str = "shell") -> tuple[str, str]:
    """Execute a cell and return (output, status) using async subprocess."""
    runner = _CELL_RUNNERS.get(language)
    if runner is None:
        return f"Unsupported language: {language}", "error"

    cmd, _ = runner
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, source,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        output = (stdout or b"") + (stderr or b"")
        output_str = output.decode(errors="replace")
        status = "success" if proc.returncode == 0 else "error"
        return output_str, status
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return "Timed out after 30s", "error"


@app.post("/chatbooks/{chatbook_id}/cells")
async def create_and_execute_cell(
    chatbook_id: str,
    body: ExecuteCell,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    """Create a cell, execute it, and store the result + Run record."""
    chatbook = await session.get(Chatbook, chatbook_id)
    if not chatbook:
        raise HTTPException(status_code=404, detail="Chatbook not found")

    # Determine next index
    result = await session.execute(
        select(Cell).where(Cell.chatbook_id == chatbook_id).order_by(Cell.index.desc()).limit(1)
    )
    last_cell = result.scalar_one_or_none()
    next_index = (last_cell.index + 1) if last_cell else 0

    # Create cell
    cell = Cell(
        chatbook_id=chatbook_id,
        index=next_index,
        language=body.language,
        source=body.source,
        status="running",
        started_at=datetime.now(UTC),
    )
    session.add(cell)
    await session.flush()

    # Execute async
    output, status = await _run_cell(body.source, body.language)

    # Create Run record for provenance
    run = Run(
        project_id=chatbook.project_id,
        process_id="",  # Cell execution bypasses PTY Process; filled below
        cell_id=cell.id,
        status=status,
        input={"language": body.language, "source": body.source},
        output=output,
        started_at=cell.started_at,
        finished_at=datetime.now(UTC),
    )
    session.add(run)

    # Update cell
    cell.status = status
    cell.output = output
    cell.finished_at = datetime.now(UTC)
    await session.flush()

    return {
        "id": cell.id,
        "index": cell.index,
        "language": cell.language,
        "source": cell.source,
        "output": cell.output,
        "status": cell.status,
        "run_id": run.id,
        "started_at": cell.started_at.isoformat() if cell.started_at else None,
        "finished_at": cell.finished_at.isoformat() if cell.finished_at else None,
    }


@app.get("/chatbooks/{chatbook_id}/cells")
async def list_cells(chatbook_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Cell).where(Cell.chatbook_id == chatbook_id).order_by(Cell.index)
    )
    return [{
        "id": c.id, "index": c.index, "language": c.language,
        "source": c.source, "output": c.output, "status": c.status,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "finished_at": c.finished_at.isoformat() if c.finished_at else None,
    } for c in result.scalars().all()]

@app.put("/chatbooks/{chatbook_id}/cells/{cell_id}")
async def update_cell(
    chatbook_id: str, cell_id: str,
    body: UpdateCell,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    cell = await session.get(Cell, cell_id)
    if not cell or cell.chatbook_id != chatbook_id:
        raise HTTPException(status_code=404, detail="Cell not found")
    if body.language is not None:
        cell.language = body.language
    if body.source is not None:
        cell.source = body.source
    await session.flush()
    return {"id": cell.id, "language": cell.language, "source": cell.source}

@app.delete("/chatbooks/{chatbook_id}/cells/{cell_id}")
async def delete_cell(chatbook_id: str, cell_id: str, _auth: str = Depends(verify_api_key), session: AsyncSession = Depends(get_session)):
    cell = await session.get(Cell, cell_id)
    if not cell or cell.chatbook_id != chatbook_id:
        raise HTTPException(status_code=404, detail="Cell not found")
    await session.delete(cell)
    await session.flush()
    return {"status": "deleted"}


# --- Tasks (advanced) ----------------------------------------------------

@app.post("/chatbooks/{chatbook_id}/messages/{message_id}/create-task")
async def create_task_from_message(
    chatbook_id: str,
    message_id: str,
    _auth: str = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    msg = await session.get(Message, message_id)
    if not msg or msg.chatbook_id != chatbook_id:
        raise HTTPException(status_code=404, detail="Message not found")

    chatbook = await session.get(Chatbook, chatbook_id)
    if not chatbook:
        raise HTTPException(status_code=404, detail="Chatbook not found")

    title = msg.content.strip().split("\n")[0][:80]
    if not title:
        title = f"Task from message {message_id[:8]}"

    task = Task(
        project_id=chatbook.project_id,
        title=title,
        created_from_ref=f"chatbook:{chatbook_id}/message:{message_id}",
    )
    session.add(task)
    await session.flush()

    return {"id": task.id, "title": task.title, "status": task.status,
            "project_id": task.project_id, "created_from_ref": task.created_from_ref}


# --- WebSocket (events + terminal output streaming) -----------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, manager: ConnectionManager = Depends(get_manager), rt: TerminalRuntime = Depends(get_terminal_runtime)):
    # Authenticate via query param when API_KEY is set
    api_key = os.environ.get("API_KEY", "")
    if api_key:
        provided = websocket.query_params.get("key", "")
        if provided != api_key:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "terminal:write":
                sess_id = data.get("session_id")
                text_data = data.get("data", "")
                if sess_id and sess_id in rt.sessions:
                    await rt.write(sess_id, text_data)
                    sess = rt.sessions[sess_id]
                    await websocket.send_json({"type": "terminal:output", "session_id": sess_id, "data": sess.buffer})
                else:
                    await websocket.send_json({"type": "error", "detail": f"session {sess_id} not found"})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/test-event")
async def test_event(_auth: str = Depends(verify_api_key), manager: ConnectionManager = Depends(get_manager)):
    """Simple in-memory broadcast for testing (SQLite no NOTIFY)."""
    event = {"type": "test", "message": "hello", "timestamp": asyncio.get_event_loop().time()}
    await manager.broadcast(event)
    return {"status": "notified", "event": event}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)