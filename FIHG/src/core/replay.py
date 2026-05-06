"""Replay and summarization for FIHG event history"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict


class ReplayEngine:
    """Replay and summarize FIHG event history.

    Provides event playback, timeline reconstruction, and summary
    generation from the SQLite event log.
    """

    def __init__(self, event_log_querier):
        """
        Args:
            event_log_querier: EventLogQuerier instance
        """
        self.querier = event_log_querier

    async def replay_events(
        self,
        fihg: Optional[str] = None,
        event_type: Optional[str] = None,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Replay events in chronological order.

        Returns list of event dicts with parsed payloads.
        """
        return await self.querier.query_events(
            fihg=fihg,
            event_type=event_type,
            time_start=time_start,
            time_end=time_end,
            limit=limit,
        )

    async def replay_timeline(
        self,
        fihg: Optional[str] = None,
        time_window_hours: float = 24.0,
    ) -> List[Dict[str, Any]]:
        """Get a timeline of recent events."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=time_window_hours)
        return await self.replay_events(
            fihg=fihg,
            time_start=start,
            time_end=now,
            limit=500,
        )

    async def summarize_session(
        self,
        session_id: str,
        fihg: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a summary of all events for a session.

        Returns:
            Dict with session_id, event_count, event_types, timeline,
            key_decisions, and metadata.
        """
        events = await self.querier.query_events(
            fihg=fihg,
            payload_contains=session_id,
            limit=1000,
        )

        if not events:
            return {
                "session_id": session_id,
                "event_count": 0,
                "event_types": {},
                "timeline": [],
                "key_decisions": [],
                "metadata": {"fihg": fihg},
            }

        # Count event types
        type_counts = defaultdict(int)
        for event in events:
            et = event.get("event_type", "unknown")
            type_counts[et] += 1

        # Extract key decisions (hyperedge resolutions, STV outcomes)
        key_decisions = []
        for event in events:
            et = event.get("event_type", "")
            if "resolve" in et.lower() or "stv" in et.lower() or "outcome" in et.lower():
                key_decisions.append({
                    "type": et,
                    "payload": event.get("payload", {}),
                    "timestamp": event.get("timestamp"),
                })

        return {
            "session_id": session_id,
            "event_count": len(events),
            "event_types": dict(type_counts),
            "timeline": [
                {
                    "timestamp": e.get("timestamp"),
                    "event_type": e.get("event_type"),
                    "fihg": e.get("fihg"),
                }
                for e in events[:50]  # First 50 events
            ],
            "key_decisions": key_decisions,
            "metadata": {"fihg": fihg},
        }

    async def summarize_graph_activity(
        self,
        fihg: str,
        time_window_hours: float = 24.0,
    ) -> Dict[str, Any]:
        """Summarize activity for a specific graph."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=time_window_hours)

        events = await self.querier.query_events(
            fihg=fihg,
            time_start=start,
            time_end=now,
            limit=1000,
        )

        if not events:
            return {
                "fihg": fihg,
                "event_count": 0,
                "time_window_hours": time_window_hours,
                "event_types": {},
                "error_count": 0,
                "summary": "No activity in the specified time window.",
            }

        type_counts = defaultdict(int)
        error_count = 0
        for event in events:
            et = event.get("event_type", "unknown")
            type_counts[et] += 1
            if "error" in et.lower() or "fail" in et.lower():
                error_count += 1

        # Build human-readable summary
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        summary_parts = [f"{fihg} graph: {len(events)} events in {time_window_hours}h"]
        for et, count in top_types:
            summary_parts.append(f"  - {et}: {count}")

        return {
            "fihg": fihg,
            "event_count": len(events),
            "time_window_hours": time_window_hours,
            "event_types": dict(type_counts),
            "error_count": error_count,
            "top_event_types": top_types,
            "summary": "\n".join(summary_parts),
        }

    async def generate_activity_report(
        self,
        time_window_hours: float = 24.0,
        include_graphs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive activity report across all graphs."""
        graphs = include_graphs or ["identity", "memory", "skills"]
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=time_window_hours)

        all_events = await self.querier.query_events(
            time_start=start,
            time_end=now,
            limit=5000,
        )

        graph_reports = {}
        for graph in graphs:
            graph_events = [e for e in all_events if e.get("fihg") == graph]
            type_counts = defaultdict(int)
            for event in graph_events:
                et = event.get("event_type", "unknown")
                type_counts[et] += 1

            graph_reports[graph] = {
                "event_count": len(graph_events),
                "event_types": dict(type_counts),
            }

        total_events = sum(r["event_count"] for r in graph_reports.values())

        return {
            "time_window_hours": time_window_hours,
            "total_events": total_events,
            "graphs": graph_reports,
            "generated_at": now.isoformat(),
        }

    async def export_session_log(
        self,
        session_id: str,
        fihg: Optional[str] = None,
    ) -> str:
        """Export session events as a JSON string for replay."""
        events = await self.querier.query_events(
            fihg=fihg,
            payload_contains=session_id,
            limit=10000,
        )
        return json.dumps(events, default=str, indent=2)

    async def import_session_log(self, log_json: str) -> int:
        """Import events from a JSON log string.

        Returns the number of events imported.
        """
        events = json.loads(log_json)
        count = 0
        # Note: In a real system, this would write back to the event log
        # For now, we just validate and count
        for event in events:
            if "event_type" in event and "fihg" in event:
                count += 1
        return count
