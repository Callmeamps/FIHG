# Superposition

Local-first production environment. Combines chat, terminal, tasks, agents, and dashboards.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Run the API server**:
   ```bash
   uv run main.py
   ```
   Server starts at http://127.0.0.1:8000. SQLite database `superposition.db` created on startup.

3. **Verify health**:
   ```bash
   curl http://127.0.0.1:8000/health
   ```
   Expected response: `{"status":"ok"}`

## Development

- API docs: http://127.0.0.1:8000/docs
- WebSocket: `ws://127.0.0.1:8000/ws`
- Trigger test event: `curl -X POST http://127.0.0.1:8000/test-event`

## Testing

```bash
pytest
```

## Project Structure

- `main.py`: FastAPI app, health, WebSocket.
- `superposition/`: core package (models, db).
- `tests/`: pytest suite.

## Notes

- Uses SQLite + `aiosqlite` for local data.
- Event streaming: In-memory broadcast to WS clients (no NOTIFY/Docker required).
- Design doc: `agent/superposition_design_doc.md`
- PRD: `agent/superposition_prd.md`
