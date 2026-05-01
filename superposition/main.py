import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel
from superposition.db import engine, Base, get_session
from superposition.terminal import TerminalRuntime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

import superposition.models  # noqa: F401
from superposition.models import Project, Task, Artifact, Agent, Process, Run, Lane, Chatbook, Message


# --- Pydantic schemas -------------------------------------------------------

class CreateProject(BaseModel):
    title: str
    description: Optional[str] = None

class CreateTask(BaseModel):
    project_id: str
    title: str
    status: Optional[str] = "todo"

class CreateChatbook(BaseModel):
    project_id: str
    title: Optional[str] = "New Chat"

class SendMessage(BaseModel):
    role: str = "user"
    content: str
    parent_id: Optional[str] = None

class SpawnTerminal(BaseModel):
    command: Optional[str] = "/bin/bash"

class WriteTerminal(BaseModel):
    data: str


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

terminal_runtime: TerminalRuntime = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global terminal_runtime
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.ws_manager = ConnectionManager()
    terminal_runtime = TerminalRuntime()

    yield
    await engine.dispose()

app = FastAPI(title="Superposition", version="0.1.0", lifespan=lifespan)


# --- Helpers ----------------------------------------------------------------

def get_manager() -> ConnectionManager:
    return app.state.ws_manager


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
async def list_projects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return [{"id": p.id, "title": p.title, "status": p.status}
            for p in result.scalars().all()]

@app.post("/projects")
async def create_project(body: CreateProject, session: AsyncSession = Depends(get_session)):
    project = Project(title=body.title, description=body.description)
    session.add(project)
    await session.flush()
    return {"id": project.id, "title": project.title, "status": project.status}


# --- Tasks ------------------------------------------------------------------

@app.post("/tasks")
async def create_task(body: CreateTask, session: AsyncSession = Depends(get_session)):
    task = Task(project_id=body.project_id, title=body.title, status=body.status)
    session.add(task)
    await session.flush()
    return {"id": task.id, "title": task.title, "status": task.status}


# --- Chatbooks -------------------------------------------------------------

@app.get("/chatbooks")
async def list_chatbooks(project_id: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    stmt = select(Chatbook).order_by(Chatbook.updated_at.desc())
    if project_id:
        stmt = stmt.where(Chatbook.project_id == project_id)
    result = await session.execute(stmt)
    return [{"id": cb.id, "title": cb.title, "project_id": cb.project_id,
             "created_at": cb.created_at.isoformat() if cb.created_at else None}
            for cb in result.scalars().all()]

@app.post("/chatbooks")
async def create_chatbook(body: CreateChatbook, session: AsyncSession = Depends(get_session)):
    cb = Chatbook(project_id=body.project_id, title=body.title)
    session.add(cb)
    await session.flush()
    return {"id": cb.id, "title": cb.title, "project_id": cb.project_id}

@app.get("/chatbooks/{chatbook_id}/messages")
async def list_messages(chatbook_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Message).where(Message.chatbook_id == chatbook_id).order_by(Message.created_at)
    )
    return [{"id": m.id, "role": m.role, "content": m.content, "parent_id": m.parent_id,
             "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in result.scalars().all()]

@app.post("/chatbooks/{chatbook_id}/messages")
async def send_message(chatbook_id: str, body: SendMessage, session: AsyncSession = Depends(get_session)):
    msg = Message(chatbook_id=chatbook_id, role=body.role, content=body.content, parent_id=body.parent_id)
    session.add(msg)
    await session.flush()
    return {"id": msg.id, "role": msg.role, "content": msg.content}


# --- Terminal sessions -----------------------------------------------------

@app.post("/terminal/spawn")
async def terminal_spawn(body: SpawnTerminal):
    sess = await terminal_runtime.spawn(command=body.command or "/bin/bash")
    return {"session_id": sess.id, "pid": sess.pid, "status": sess.status}

@app.post("/terminal/{session_id}/write")
async def terminal_write(session_id: str, body: WriteTerminal):
    await terminal_runtime.write(session_id, body.data)
    return {"status": "ok"}

@app.post("/terminal/{session_id}/resize")
async def terminal_resize(session_id: str, cols: int = Query(80), rows: int = Query(24)):
    await terminal_runtime.resize(session_id, cols, rows)
    return {"status": "ok"}

@app.post("/terminal/{session_id}/close")
async def terminal_close(session_id: str):
    await terminal_runtime.close(session_id)
    return {"status": "closed"}

@app.get("/terminal/sessions")
async def list_terminal_sessions():
    return {"sessions": [{"id": s.id, "status": s.status, "pid": s.pid}
                         for s in terminal_runtime.sessions.values()]}


# --- WebSocket (events + terminal output streaming) -----------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, manager: ConnectionManager = Depends(get_manager)):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "terminal:write":
                sess_id = data.get("session_id")
                text_data = data.get("data", "")
                if sess_id and sess_id in terminal_runtime.sessions:
                    await terminal_runtime.write(sess_id, text_data)
                    # Echo back current buffer
                    sess = terminal_runtime.sessions[sess_id]
                    await websocket.send_json({"type": "terminal:output", "session_id": sess_id, "data": sess.buffer})
                else:
                    await websocket.send_json({"type": "error", "detail": f"session {sess_id} not found"})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/test-event")
async def test_event(manager: ConnectionManager = Depends(get_manager)):
    """Simple in-memory broadcast for testing (SQLite no NOTIFY)."""
    event = {"type": "test", "message": "hello", "timestamp": asyncio.get_event_loop().time()}
    await manager.broadcast(event)
    return {"status": "notified", "event": event}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)