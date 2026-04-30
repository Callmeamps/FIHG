# Superposition

Local-first production workspace. Combines chat, terminal, tasks, agents, and dashboards.

## Quick Start

1. **Start PostgreSQL** (choose one):

   Using Docker (recommended):
   ```bash
   docker compose up -d
   ```

   Or ensure a PostgreSQL instance is running at `localhost:5432` with:
   - database: `superposition`
   - user: `postgres`
   - password: `postgres`

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. **Run the API server**:

   ```bash
   uv run main.py
   ```

   Server starts at http://127.0.0.1:8000

4. **Verify health**:

   ```bash
   curl http://127.0.0.1:8000/health
   ```

   Expected response: `{"status":"ok"}`

## Development

- API docs: http://127.0.0.1:8000/docs (Swagger UI)
- WebSocket: `ws://127.0.0.1:8000/ws`
- Trigger test event: `curl -X POST http://127.0.0.1:8000/test-event`

## Testing

```bash
pytest
```

Requires PostgreSQL running.

## Project Structure

- `main.py`: FastAPI app, health, WebSocket, test-event.
- `superposition/`: core package (models, db).
- `tests/`: pytest suite.
- `docker-compose.yml`: dev PostgreSQL.

## Notes

- Schema auto-created on startup via `Base.metadata.create_all`.
- Event streaming: PostgreSQL NOTIFY on channel `superposition_events` broadcasts to WS clients.
- Design doc: `agent/superposition_design_doc.md`
- PRD: `agent/superposition_prd.md`
