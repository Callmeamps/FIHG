"""Tests for HyperedgeManager"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta

from src.db.sqlite_schema import SQLiteSchema
from src.core.hyperedges import HyperedgeManager


@pytest.fixture
async def sqlite_db():
    db = SQLiteSchema(":memory:")
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def manager(sqlite_db):
    return HyperedgeManager(sqlite_db)


@pytest.fixture
async def seeded_hyperedges(manager):
    """Seed test hyperedges."""
    edges = []
    # Multi-party consensus in identity
    he1 = await manager.create_hyperedge(
        event_type="multi_agent_consensus",
        participants=["agent_a", "agent_b", "agent_c"],
        role_map={"agent_a": "initiator", "agent_b": "voter", "agent_c": "voter"},
        graph="identity",
        score_vector={"consensus_strength": 0.85},
        provenance="test",
    )
    edges.append(he1)

    # Cross-graph sync in memory
    he2 = await manager.create_hyperedge(
        event_type="cross_graph_sync",
        participants=["mem_1", "mem_2"],
        role_map={"mem_1": "source", "mem_2": "target"},
        graph="memory",
        score_vector={"sync_quality": 0.92},
        provenance="test",
    )
    edges.append(he2)

    # Another identity event with agent_a
    he3 = await manager.create_hyperedge(
        event_type="multi_agent_consensus",
        participants=["agent_a", "agent_d"],
        role_map={"agent_a": "voter", "agent_d": "initiator"},
        graph="identity",
        score_vector={"consensus_strength": 0.67},
        provenance="test",
    )
    edges.append(he3)

    return edges


@pytest.mark.asyncio
async def test_create_hyperedge(manager):
    he = await manager.create_hyperedge(
        event_type="test_event",
        participants=["p1", "p2"],
        role_map={"p1": "initiator", "p2": "responder"},
        graph="identity",
        score_vector={"quality": 0.8},
    )
    assert he.id.startswith("he_")
    assert he.event_type == "test_event"
    assert len(he.participants) == 2
    assert he.role_map["p1"] == "initiator"


@pytest.mark.asyncio
async def test_get_hyperedge(manager, seeded_hyperedges):
    he_id = seeded_hyperedges[0].id
    result = await manager.get_hyperedge(he_id)
    assert result is not None
    assert result["hyperedge_id"] == he_id
    assert result["event_type"] == "multi_agent_consensus"


@pytest.mark.asyncio
async def test_get_hyperedge_not_found(manager):
    result = await manager.get_hyperedge("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_query_hyperedges_by_graph(manager, seeded_hyperedges):
    results = await manager.query_hyperedges(graph="identity")
    assert len(results) == 2
    assert all(r.get("event_type") == "multi_agent_consensus" for r in results)


@pytest.mark.asyncio
async def test_query_hyperedges_by_event_type(manager, seeded_hyperedges):
    results = await manager.query_hyperedges(event_type="cross_graph_sync")
    assert len(results) == 1
    assert results[0]["event_type"] == "cross_graph_sync"


@pytest.mark.asyncio
async def test_query_hyperedges_by_participant(manager, seeded_hyperedges):
    results = await manager.query_hyperedges(participant="agent_a")
    assert len(results) == 2  # agent_a is in two hyperedges


@pytest.mark.asyncio
async def test_query_hyperedges_with_limit(manager, seeded_hyperedges):
    results = await manager.query_hyperedges(limit=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_get_participant_history(manager, seeded_hyperedges):
    history = await manager.get_participant_history("agent_a")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_get_multi_party_events(manager, seeded_hyperedges):
    # Default min_participants=3
    results = await manager.get_multi_party_events(min_participants=3)
    assert len(results) == 1  # Only the 3-participant consensus
    assert len(results[0]["participants"]) == 3


@pytest.mark.asyncio
async def test_get_multi_party_events_lower_threshold(manager, seeded_hyperedges):
    results = await manager.get_multi_party_events(min_participants=2)
    assert len(results) == 3  # All have >= 2 participants


@pytest.mark.asyncio
async def test_resolve_hyperedge(manager, seeded_hyperedges):
    he_id = seeded_hyperedges[0].id
    result = await manager.resolve_hyperedge(he_id, "consensus_reached", ["agent_b"])
    assert result is True


@pytest.mark.asyncio
async def test_resolve_nonexistent_hyperedge(manager):
    result = await manager.resolve_hyperedge("nonexistent", "failed")
    assert result is False


@pytest.mark.asyncio
async def test_get_hyperedge_stats(manager, seeded_hyperedges):
    stats = await manager.get_hyperedge_stats()
    assert stats["total"] == 3
    assert stats["by_type"]["multi_agent_consensus"] == 2
    assert stats["by_type"]["cross_graph_sync"] == 1
    assert stats["avg_participants"] == pytest.approx(7/3, rel=0.01)
    assert stats["by_graph"]["identity"] == 2
    assert stats["by_graph"]["memory"] == 1


@pytest.mark.asyncio
async def test_get_hyperedge_stats_empty(manager):
    stats = await manager.get_hyperedge_stats()
    assert stats["total"] == 0
    assert stats["by_type"] == {}
    assert stats["avg_participants"] == 0
