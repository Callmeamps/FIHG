"""Session state persistence across Identity, Memory, and Skills FIHGs"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone


class SessionStateManager:
    """Manage session state persistence across the three FIHG graphs.

    Provides save/load/update/clear operations for per-session state,
    including graph-specific sub-states and cross-graph coordination data.
    """

    def __init__(self, sqlite_db):
        """
        Args:
            sqlite_db: SQLiteSchema instance with active connection
        """
        self.db = sqlite_db

    async def save_state(
        self,
        session_id: str,
        identity_state: Optional[Dict] = None,
        memory_state: Optional[Dict] = None,
        skills_state: Optional[Dict] = None,
    ) -> None:
        """Save or upsert full session state across all three graphs.

        Args:
            session_id: Unique session identifier
            identity_state: Current Identity FIHG state snapshot
            memory_state: Current Memory FIHG state snapshot
            skills_state: Current Skills FIHG state snapshot
        """
        await self.db.save_session_state(
            session_id=session_id,
            identity_state=identity_state,
            memory_state=memory_state,
            skills_state=skills_state,
        )

    async def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load full session state.

        Args:
            session_id: Session identifier to load

        Returns:
            Dict with identity_state, memory_state, skills_state keys,
            or None if session doesn't exist.
        """
        return await self.db.get_session_state(session_id)

    async def update_state(
        self,
        session_id: str,
        graph: str,
        key: str,
        value: Any,
    ) -> None:
        """Update a single key within a graph's sub-state.

        Performs a read-modify-write on the session_state row.

        Args:
            session_id: Session identifier
            graph: One of 'identity', 'memory', 'skills'
            key: Key to update within the graph's state dict
            value: New value (must be JSON-serializable)
        """
        state = await self.load_state(session_id) or {
            "identity_state": {},
            "memory_state": {},
            "skills_state": {},
        }

        graph_key_map = {
            "identity": "identity_state",
            "memory": "memory_state",
            "skills": "skills_state",
        }
        db_key = graph_key_map.get(graph)
        if not db_key:
            raise ValueError(f"Unknown graph: {graph}. Must be one of {list(graph_key_map.keys())}")

        graph_state = state.get(db_key) or {}
        graph_state[key] = value
        state[db_key] = graph_state

        await self.save_state(
            session_id=session_id,
            identity_state=state.get("identity_state"),
            memory_state=state.get("memory_state"),
            skills_state=state.get("skills_state"),
        )

    async def clear_state(self, session_id: str) -> bool:
        """Delete session state entirely.

        Args:
            session_id: Session to clear

        Returns:
            True if a row was deleted, False if session didn't exist.
        """
        conn = self.db._db
        cursor = await conn.execute(
            "DELETE FROM session_state WHERE session_id = ?",
            (session_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def list_sessions(self) -> List[str]:
        """List all active session IDs, ordered by most recently updated."""
        conn = self.db._db
        cursor = await conn.execute(
            "SELECT session_id FROM session_state ORDER BY updated_at DESC",
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_graph_state(
        self,
        session_id: str,
        graph: str,
    ) -> Optional[Dict]:
        """Get state for a single graph within a session.

        Args:
            session_id: Session identifier
            graph: One of 'identity', 'memory', 'skills'

        Returns:
            Dict of graph state, or None if session doesn't exist.
        """
        state = await self.load_state(session_id)
        if state is None:
            return None

        graph_key_map = {
            "identity": "identity_state",
            "memory": "memory_state",
            "skills": "skills_state",
        }
        db_key = graph_key_map.get(graph)
        if not db_key:
            raise ValueError(f"Unknown graph: {graph}")

        return state.get(db_key) or {}

    async def get_session_age(self, session_id: str) -> Optional[float]:
        """Get session age in seconds since last update.

        Args:
            session_id: Session identifier

        Returns:
            Age in seconds, or None if session doesn't exist.
        """
        conn = self.db._db
        cursor = await conn.execute(
            "SELECT updated_at FROM session_state WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        updated_at = datetime.fromisoformat(row[0])
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        return (now_utc - updated_at).total_seconds()

    async def prune_stale_sessions(self, max_age_seconds: float = 86400) -> int:
        """Delete sessions older than max_age_seconds.

        Args:
            max_age_seconds: Sessions older than this are removed (default: 24h)

        Returns:
            Number of sessions pruned.
        """
        conn = self.db._db
        cursor = await conn.execute(
            "SELECT session_id, updated_at FROM session_state",
        )
        rows = await cursor.fetchall()

        now = datetime.now()
        stale_ids = []
        for session_id, updated_at_str in rows:
            updated_at = datetime.fromisoformat(updated_at_str)
            if (now - updated_at).total_seconds() > max_age_seconds:
                stale_ids.append(session_id)

        if stale_ids:
            placeholders = ",".join("?" * len(stale_ids))
            await conn.execute(
                f"DELETE FROM session_state WHERE session_id IN ({placeholders})",
                stale_ids,
            )
            await conn.commit()

        return len(stale_ids)
