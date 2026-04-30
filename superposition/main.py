import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from superposition.db import engine, Base, get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Import models to register them with Base.metadata
import superposition.models  # noqa: F401

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    app.state.ws_manager = ConnectionManager()
    
    yield
    await engine.dispose()

app = FastAPI(title="Superposition", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def get_manager() -> ConnectionManager:
    return app.state.ws_manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, manager: ConnectionManager = Depends(get_manager)):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
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
