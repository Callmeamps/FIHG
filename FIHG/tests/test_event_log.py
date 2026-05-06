"""Tests for EventLogQuerier"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta

from src.db.sqlite_schema import SQLiteSchema
from src.db.event_log import EventLogQuerier


@pytest.fixture
async def sqlite_db():
    """Create an in-memory SQLite database with schema."""
    db = SQLiteSchema(":memory:")
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def querier(sqlite_db):
    return EventLogQuerier(sqlite_db)


@pytest.fixture
async def seeded_events(querier):
    """Seed test events."""
    events = [
        ("identity", "vote_cast", {"candidate": "a", "thread_id": "t1"}),
        ("identity", "vote_cast", {"candidate": "b", "thread_id": "t1"}),
        ("identity", "election_complete", {"winner": "a", "thread_id": "t1"}),
        ("memory", "episode_stored", {"context": "ctx1", "thread_id": "t2"}),
        ("memory", "retrieval", {"query": "test", "thread_id": "t2"}),
        ("skills", "skill_invoked", {"skill": "summarize", "thread_id": "t3"}),
        ("skills", "error", {"error_type": "timeout", "entity_id": "skill_1", "thread_id": "t3"}),
        ("skills", "error", {"error_type": "not_found", "entity_id": "skill_2", "thread_id": "t3"}),
    ]
    for fihg, event_type, payload in events:
        db = querier.db
        await db.log_event(fihg, event_type, payload)
    return events


@pytest.mark.asyncio
async def test_query_all_events(querier, seeded_events):
    events = await querier.query_events()
    assert len(events) == len(seeded_events)


@pytest.mark.asyncio
async def test_query_by_fihg(querier, seeded_events):
    events = await querier.query_events(fihg="identity")
    assert len(events) == 3
    assert all(e["fihg"] == "identity" for e in events)


@pytest.mark.asyncio
async def test_query_by_event_type(querier, seeded_events):
    events = await querier.query_events(event_type="error")
    assert len(events) == 2
    assert all(e["event_type"] == "error" for e in events)


@pytest.mark.asyncio
async def test_query_with_limit(querier, seeded_events):
    events = await querier.query_events(limit=3)
    assert len(events) == 3


@pytest.mark.asyncio
async def test_aggregate_by_event_type(querier, seeded_events):
    agg = await querier.aggregate_events(group_by="event_type")
    assert agg["total"] == 8
    assert agg["groups"]["vote_cast"] == 2
    assert agg["groups"]["error"] == 2


@pytest.mark.asyncio
async def test_aggregate_by_fihg(querier, seeded_events):
    agg = await querier.aggregate_events(group_by="fihg")
    assert agg["groups"]["identity"] == 3
    assert agg["groups"]["memory"] == 2
    assert agg["groups"]["skills"] == 3


@pytest.mark.asyncio
async def test_aggregate_with_fihg_filter(querier, seeded_events):
    agg = await querier.aggregate_events(group_by="event_type", fihg="skills")
    assert agg["total"] == 3
    assert agg["groups"]["skill_invoked"] == 1
    assert agg["groups"]["error"] == 2


@pytest.mark.asyncio
async def test_aggregate_by_payload_key(querier, seeded_events):
    agg = await querier.aggregate_events(group_by="payload.error_type", fihg="skills")
    assert "timeout" in agg["groups"]
    assert "not_found" in agg["groups"]


@pytest.mark.asyncio
async def test_get_error_summary(querier, seeded_events):
    summary = await querier.get_error_summary()
    assert summary["total_errors"] == 2
    assert summary["error_types"]["timeout"] == 1
    assert summary["error_types"]["not_found"] == 1
    assert summary["affected_entities"]["skill_1"] == 1


@pytest.mark.asyncio
async def test_get_error_summary_by_fihg(querier, seeded_events):
    summary = await querier.get_error_summary(fihg="identity")
    assert summary["total_errors"] == 0


@pytest.mark.asyncio
async def test_get_fihg_activity_report(querier, seeded_events):
    report = await querier.get_fihg_activity_report(time_window=timedelta(hours=1))
    assert "identity" in report
    assert "memory" in report
    assert "skills" in report
    assert report["identity"]["total"] == 3
    assert report["skills"]["total"] == 3
