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
from superposition.models import Project, Task, Artifact, Agent, Process, Run, Lane, Chatbook, Message, Cell


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