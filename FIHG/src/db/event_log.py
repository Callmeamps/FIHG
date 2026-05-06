"""Event log querying and aggregation utilities for FIHG peripheral storage"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from collections import defaultdict


class EventLogQuerier:
    """Advanced querying and aggregation over the SQLite event_log table"""

    def __init__(self, sqlite_db):
        """
        Args:
            sqlite_db: SQLiteSchema instance with active connection
        """
        self.db = sqlite_db

    async def query_events(
        self,
        fihg: Optional[str] = None,
        event_type: Optional[str] = None,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
        payload_contains: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query events with flexible filters.

        Args:
            fihg: Filter by FIHG graph name (identity/memory/skills)
            event_type: Filter by event type
            time_start: Start of time window
            time_end: End of time window
            payload_contains: Substring match in payload JSON
            limit: Max results
            offset: Pagination offset

        Returns:
            List of event dicts with parsed payload
        """
        conditions = []
        params = []

        if fihg:
            conditions.append("fihg = ?")
            params.append(fihg)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if time_start:
            conditions.append("timestamp >= ?")
            params.append(time_start.strftime("%Y-%m-%d %H:%M:%S"))
        if time_end:
            conditions.append("timestamp <= ?")
            params.append(time_end.strftime("%Y-%m-%d %H:%M:%S"))

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM event_log WHERE {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await self.db._db.execute(query, params)
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            event = {
                "id": row[0],
                "timestamp": row[1],
                "fihg": row[2],
                "event_type": row[3],
                "payload": json.loads(row[4]) if row[4] else None,
            }
            if payload_contains:
                payload_str = json.dumps(event["payload"]) if event["payload"] else ""
                if payload_contains.lower() not in payload_str.lower():
                    continue
            result.append(event)

        return result

    async def aggregate_events(
        self,
        group_by: str = "event_type",
        time_window: Optional[timedelta] = None,
        fihg: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate events by field.

        Args:
            group_by: Column to group by (event_type, fihg, or payload key as 'payload.key')
            time_window: Optional time window for aggregation
            fihg: Optional filter by graph name

        Returns:
            Dict with {groups: {group_value: count}, total: int, time_window: str}
        """
        conditions = []
        params = []

        if time_window:
            cutoff = (datetime.now(timezone.utc) - time_window).strftime("%Y-%m-%d %H:%M:%S")
            conditions.append("timestamp >= ?")
            params.append(cutoff)
        if fihg:
            conditions.append("fihg = ?")
            params.append(fihg)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM event_log WHERE {where_clause} ORDER BY timestamp DESC"

        cursor = await self.db._db.execute(query, params)
        rows = await cursor.fetchall()

        groups = defaultdict(int)
        for row in rows:
            event = {
                "id": row[0],
                "timestamp": row[1],
                "fihg": row[2],
                "event_type": row[3],
                "payload": json.loads(row[4]) if row[4] else None,
            }

            if group_by == "event_type":
                key = event["event_type"]
            elif group_by == "fihg":
                key = event["fihg"]
            elif group_by.startswith("payload."):
                key_name = group_by.split(".", 1)[1]
                key = str(event.get("payload", {}).get(key_name, "unknown"))
            else:
                key = "unknown"

            groups[key] += 1

        return {
            "groups": dict(groups),
            "total": len(rows),
            "time_window": str(time_window) if time_window else "all_time",
            "group_by": group_by,
        }

    async def get_event_timeline(
        self,
        thread_id: str,
        max_events: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get chronological event timeline for a thread.

        Args:
            thread_id: Thread identifier
            max_events: Maximum events to return

        Returns:
            List of events ordered by timestamp
        """
        events = await self.query_events(
            payload_contains=f'"thread_id": "{thread_id}"',
            limit=max_events * 2,  # Over-fetch to account for payload filter
        )

        # Filter to only events matching this thread_id in payload
        thread_events = []
        for event in events:
            if event["payload"] and event["payload"].get("thread_id") == thread_id:
                thread_events.append(event)
                if len(thread_events) >= max_events:
                    break

        # Sort by timestamp ascending for timeline view
        thread_events.sort(key=lambda e: e["timestamp"])
        return thread_events

    async def get_error_summary(
        self,
        fihg: Optional[str] = None,
        time_window: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """Get summary of error events.

        Args:
            fihg: Optional filter by graph name
            time_window: Optional time window

        Returns:
            Dict with error counts, types, and affected entities
        """
        error_events = await self.query_events(
            fihg=fihg,
            event_type="error",
            time_start=(datetime.now() - time_window) if time_window else None,
            limit=1000,
        )

        error_types = defaultdict(int)
        affected_entities = defaultdict(int)

        for event in error_events:
            payload = event.get("payload") or {}
            error_type = payload.get("error_type", "unknown")
            entity = payload.get("entity_id", "unknown")
            error_types[error_type] += 1
            affected_entities[entity] += 1

        return {
            "total_errors": len(error_events),
            "error_types": dict(error_types),
            "affected_entities": dict(affected_entities),
            "time_window": str(time_window) if time_window else "all_time",
        }

    async def get_fihg_activity_report(
        self,
        time_window: timedelta = timedelta(hours=24),
    ) -> Dict[str, Any]:
        """Get activity report across all FIHG graphs.

        Args:
            time_window: Time window for report

        Returns:
            Dict with per-graph activity stats
        """
        report = {}
        for graph in ["identity", "memory", "skills"]:
            agg = await self.aggregate_events(
                group_by="event_type",
                time_window=time_window,
                fihg=graph,
            )
            report[graph] = agg

        return report
