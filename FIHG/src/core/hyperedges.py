"""Hyperedge management for multi-party events across FIHG graphs"""

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from ..core.base import BaseHyperedge
from ..db.event_log import EventLogQuerier


class HyperedgeManager:
    """Manage hyperedges for multi-party events across Identity, Memory, and Skills graphs.

    Hyperedges are modeled as vertices with participant links (no native hyperedge
    support in ArcadeDB). This manager provides creation, querying, and lifecycle
    operations for multi-party events.
    """

    def __init__(self, sqlite_db, arcedb_clients: Optional[Dict[str, Any]] = None):
        self.db = sqlite_db
        self.arcedb = arcedb_clients or {}
        self.querier = EventLogQuerier(sqlite_db)

    async def create_hyperedge(
        self,
        event_type: str,
        participants: List[str],
        role_map: Optional[Dict[str, str]] = None,
        graph: str = "identity",
        score_vector: Optional[Dict[str, float]] = None,
        time_window_start: Optional[datetime] = None,
        time_window_end: Optional[datetime] = None,
        provenance: str = "",
        metadata: Optional[Dict] = None,
    ) -> BaseHyperedge:
        now = datetime.now(timezone.utc)
        hyperedge = BaseHyperedge(
            id=f"he_{now.strftime('%Y%m%d%H%M%S')}_{len(participants)}",
            participants=participants,
            role_map=role_map or {},
            event_type=event_type,
            score_vector=score_vector or {},
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            provenance=provenance,
            created_at=now,
        )

        payload = {
            "hyperedge_id": hyperedge.id,
            "event_type": hyperedge.event_type,
            "participants": hyperedge.participants,
            "role_map": hyperedge.role_map,
            "score_vector": hyperedge.score_vector,
            "provenance": hyperedge.provenance,
            "fihg": graph,
            "metadata": metadata or {},
        }
        await self.db.log_event(graph, "hyperedge_created", payload)

        if graph in self.arcedb:
            await self._persist_to_arcedb(graph, hyperedge, metadata)

        return hyperedge

    async def get_hyperedge(self, hyperedge_id: str, graph: Optional[str] = None) -> Optional[Dict[str, Any]]:
        events = await self.querier.query_events(
            fihg=graph, event_type="hyperedge_created", limit=1000,
        )
        for event in events:
            payload = event.get("payload", {})
            if payload.get("hyperedge_id") == hyperedge_id:
                return payload
        return None

    async def query_hyperedges(
        self,
        graph: Optional[str] = None,
        event_type: Optional[str] = None,
        participant: Optional[str] = None,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        events = await self.querier.query_events(
            fihg=graph,
            event_type="hyperedge_created" if event_type else None,
            time_start=time_start,
            time_end=time_end,
            limit=limit * 2,
        )

        results = []
        for event in events:
            payload = event.get("payload") or {}
            if not payload.get("hyperedge_id"):
                continue
            if event_type and payload.get("event_type") != event_type:
                continue
            if participant and participant not in payload.get("participants", []):
                continue
            results.append(payload)
            if len(results) >= limit:
                break
        return results

    async def get_participant_history(self, participant_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return await self.query_hyperedges(participant=participant_id, limit=limit)

    async def get_multi_party_events(
        self, min_participants: int = 3, graph: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        all_events = await self.query_hyperedges(graph=graph, limit=1000)
        return [e for e in all_events if len(e.get("participants", [])) >= min_participants]

    async def resolve_hyperedge(
        self, hyperedge_id: str, outcome: str, runner_ups: Optional[List[str]] = None,
    ) -> bool:
        events = await self.querier.query_events(event_type="hyperedge_created", limit=1000)
        for event in events:
            payload = event.get("payload", {})
            if payload.get("hyperedge_id") == hyperedge_id:
                await self.db.log_event(
                    event.get("fihg", "unknown"),
                    "hyperedge_resolved",
                    {
                        "hyperedge_id": hyperedge_id,
                        "outcome": outcome,
                        "runner_ups": runner_ups or [],
                        "resolved_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                return True
        return False

    async def get_hyperedge_stats(self, graph: Optional[str] = None) -> Dict[str, Any]:
        events = await self.query_hyperedges(graph=graph, limit=10000)
        if not events:
            return {"total": 0, "by_type": {}, "avg_participants": 0, "by_graph": {}}

        by_type: Dict[str, int] = {}
        total_participants = 0
        by_graph: Dict[str, int] = {}

        for event in events:
            et = event.get("event_type", "unknown")
            by_type[et] = by_type.get(et, 0) + 1
            total_participants += len(event.get("participants", []))
            gn = event.get("fihg", "unknown")
            by_graph[gn] = by_graph.get(gn, 0) + 1

        return {
            "total": len(events),
            "by_type": by_type,
            "avg_participants": total_participants / len(events),
            "by_graph": by_graph,
        }

    async def _persist_to_arcedb(
        self, graph: str, hyperedge: BaseHyperedge, metadata: Optional[Dict] = None,
    ) -> None:
        client = self.arcedb.get(graph)
        if not client:
            return

        try:
            await client.submit_async(
                'g.addV("Hyperedge").property("id", id_val).property("event_type", et_val)'
                '.property("participants", p_val).property("role_map", r_val)'
                '.property("score_vector", s_val).property("created_at", c_val)',
                bindings={
                    "id_val": hyperedge.id,
                    "et_val": hyperedge.event_type,
                    "p_val": json.dumps(hyperedge.participants),
                    "r_val": json.dumps(hyperedge.role_map),
                    "s_val": json.dumps(hyperedge.score_vector),
                    "c_val": hyperedge.created_at.isoformat(),
                },
            )
            for participant_id in hyperedge.participants:
                role = hyperedge.role_map.get(participant_id, "participant")
                await client.submit_async(
                    'g.V().has("id", participant_id).as("p")'
                    '.V().has("Hyperedge", "id", he_id).as("he")'
                    '.addE("PARTICIPATES_IN").from("p").to("he").property("role", role_val)',
                    bindings={
                        "participant_id": participant_id,
                        "he_id": hyperedge.id,
                        "role_val": role,
                    },
                )
        except Exception:
            await self.db.log_event(
                graph, "hyperedge_persist_error",
                {"hyperedge_id": hyperedge.id, "error": "Failed to persist to ArcadeDB"},
            )
