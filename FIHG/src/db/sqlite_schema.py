"""SQLite peripheral store schema and operations"""

import aiosqlite
import json
from typing import Optional
from datetime import datetime


class SQLiteSchema:
    """SQLite schema for FIHG peripheral storage"""
    
    def __init__(self, db_path: str = "fihg.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Connect to SQLite and initialize schema"""
        self._db = await aiosqlite.connect(self.db_path)
        await self._init_schema()
    
    async def disconnect(self):
        """Close database connection"""
        if self._db:
            await self._db.close()
    
    async def _init_schema(self):
        """Initialize all tables"""
        async with self._db.execute("PRAGMA journal_mode=WAL"):
            pass
        
        # event_log table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                fihg TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT
            )
        """)
        
        # threads table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)
        
        # user_interactions table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                user_input TEXT NOT NULL,
                synth_output TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            )
        """)
        
        # session_state table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS session_state (
                session_id TEXT PRIMARY KEY,
                last_identity_state TEXT,
                last_memory_state TEXT,
                last_skills_state TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # metrics table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fihg TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                activity_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                last_updated TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(fihg, entity_id)
            )
        """)
        
        # stv_outcomes table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS stv_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                winner TEXT NOT NULL,
                runner_ups_json TEXT,
                rejected TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        await self._db.commit()
    
    # Event log operations
    async def log_event(self, fihg: str, event_type: str, payload: dict = None):
        """Log an event to the event_log table"""
        payload_json = json.dumps(payload) if payload else None
        await self._db.execute(
            "INSERT INTO event_log (fihg, event_type, payload_json) VALUES (?, ?, ?)",
            (fihg, event_type, payload_json)
        )
        await self._db.commit()
    
    async def get_events(self, fihg: str = None, limit: int = 100) -> list:
        """Retrieve events, optionally filtered by FIHG"""
        if fihg:
            cursor = await self._db.execute(
                "SELECT * FROM event_log WHERE fihg = ? ORDER BY timestamp DESC LIMIT ?",
                (fihg, limit)
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM event_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        return await cursor.fetchall()
    
    # Session state operations
    async def save_session_state(self, session_id: str, identity_state: dict = None,
                                 memory_state: dict = None, skills_state: dict = None):
        """Save or update session state"""
        await self._db.execute("""
            INSERT INTO session_state (session_id, last_identity_state, last_memory_state, 
                                       last_skills_state, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                last_identity_state = excluded.last_identity_state,
                last_memory_state = excluded.last_memory_state,
                last_skills_state = excluded.last_skills_state,
                updated_at = datetime('now')
        """, (session_id, json.dumps(identity_state), json.dumps(memory_state), 
              json.dumps(skills_state)))
        await self._db.commit()
    
    async def get_session_state(self, session_id: str) -> dict:
        """Retrieve session state"""
        cursor = await self._db.execute(
            "SELECT * FROM session_state WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "session_id": row[0],
                "identity_state": json.loads(row[1]) if row[1] else {},
                "memory_state": json.loads(row[2]) if row[2] else {},
                "skills_state": json.loads(row[3]) if row[3] else {},
            }
        return None
    
    # Metrics operations
    async def update_metrics(self, fihg: str, entity_id: str, 
                             activity_delta: int = 0, error_delta: int = 0):
        """Update metrics for an entity"""
        await self._db.execute("""
            INSERT INTO metrics (fihg, entity_id, activity_count, error_count, last_updated)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(fihg, entity_id) DO UPDATE SET
                activity_count = activity_count + excluded.activity_count,
                error_count = error_count + excluded.error_count,
                success_rate = CASE 
                    WHEN activity_count + excluded.activity_count > 0 
                    THEN CAST(activity_count - error_count AS REAL) / (activity_count + excluded.activity_count)
                    ELSE 1.0 END,
                last_updated = datetime('now')
        """, (fihg, entity_id, activity_delta, error_delta))
        await self._db.commit()
    
    async def get_metrics(self, fihg: str, entity_id: str) -> dict:
        """Get metrics for an entity"""
        cursor = await self._db.execute(
            "SELECT * FROM metrics WHERE fihg = ? AND entity_id = ?",
            (fihg, entity_id)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "fihg": row[1],
                "entity_id": row[2],
                "activity_count": row[3],
                "error_count": row[4],
                "success_rate": row[5],
                "last_updated": row[6]
            }
        return None
    
    # STV outcomes operations
    async def save_stv_outcome(self, task_id: str, winner: str, 
                               runner_ups: list[str] = None, rejected: list[str] = None):
        """Save STV election outcome"""
        await self._db.execute("""
            INSERT INTO stv_outcomes (task_id, winner, runner_ups_json, rejected, timestamp)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (task_id, winner, json.dumps(runner_ups or []), json.dumps(rejected or [])))
        await self._db.commit()
    
    async def get_stv_outcome(self, task_id: str) -> dict:
        """Get STV outcome for a task"""
        cursor = await self._db.execute(
            "SELECT * FROM stv_outcomes WHERE task_id = ? ORDER BY timestamp DESC LIMIT 1",
            (task_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "task_id": row[1],
                "winner": row[2],
                "runner_ups": json.loads(row[3]) if row[3] else [],
                "rejected": json.loads(row[4]) if row[4] else [],
                "timestamp": row[5]
            }
        return None