import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from superposition.db import engine, Base, get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Import models to register them with Base.metadata
import superposition.models  # noqa: F401

# =========================
# WebSocket Connection Manager
# =========================
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
                # Optionally remove dead connections
                pass

# =========================
# PostgreSQL NOTIFY Listener
# =========================
async def handle_notification(connection, pid, channel, payload):
    """Callback for asyncpg NOTIFY events."""
    try:
        data = json.loads(payload)
    except Exception:
        data = payload
    manager = app.state.ws_manager
    await manager.broadcast({
        "type": "notification",
        "channel": channel,
        "payload": data,
        "pid": pid
    })

async def pg_notifier(app: FastAPI):
    """Background task that listens to Postgres NOTIFY events and broadcasts to WS clients."""
    from superposition.db import engine as db_engine
    conn = None
    while True:
        try:
            conn = await db_engine.connect()
            raw = conn.connection  # asyncpg.Connection
            await raw.add_listener('superposition_events', handle_notification)
            # Keep the task alive; the listener runs in the background
            while True:
                await asyncio.sleep(3600)
        except Exception as e:
            print(f"Notifier error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        finally:
            if conn:
                await conn.close()

# =========================
# FastAPI Lifespan
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Warning: database not available on startup: {e}")

    # Initialize WS manager
    app.state.ws_manager = ConnectionManager()

    # Start NOTIFIER background task
    notifier_task = asyncio.create_task(pg_notifier(app))
    app.state.notifier_task = notifier_task

    try:
        yield
    finally:
        # Shutdown
        notifier_task.cancel()
        try:
            await notifier_task
        except asyncio.CancelledError:
            pass
        await engine.dispose()

app = FastAPI(title="Superposition", version="0.1.0", lifespan=lifespan)

# =========================
# Health Endpoint
# =========================
@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# =========================
# WebSocket Endpoint
# =========================
def get_manager() -> ConnectionManager:
    return app.state.ws_manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, manager: ConnectionManager = Depends(get_manager)):
    await manager.connect(websocket)
    try:
        while True:
            # Receive and ignore incoming; keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# =========================
# Test Event Endpoint (dev only)
# =========================
@app.post("/test-event")
async def test_event(session: AsyncSession = Depends(get_session)):
    """Send a test NOTIFY event to verify WS + NOTIFY integration."""
    event = {"type": "test", "message": "hello", "timestamp": asyncio.get_event_loop().time()}
    payload = json.dumps(event)
    await session.execute(text("NOTIFY superposition_events, :payload"), {"payload": payload})
    await session.commit()
    return {"status": "notified", "event": event}

# Placeholder: include routers later
# from superposition.routers import projects, tasks, artifacts

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
