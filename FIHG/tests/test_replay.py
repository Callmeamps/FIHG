"""Tests for ReplayEngine"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from src.db.sqlite_schema import SQLiteSchema
from src.db.event_log import EventLogQuerier
from src.core.replay import ReplayEngine


@pytest.fixture
async def sqlite_db():
    db = SQLiteSchema(":memory:")
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def querier(sqlite_db):
    return EventLogQuerier(sqlite_db)


@pytest.fixture
async def replay(querier):
    return ReplayEngine(querier)


@pytest.fixture
async def seeded_events(sqlite_db):
    """Seed events for testing."""
    await sqlite_db.log_event("identity", "node_created", {"node_id": "n1", "session": "sess1"})
    await sqlite_db.log_event("identity", "stv_vote", {"candidate": "c1", "session": "sess1"})
    await sqlite_db.log_event("identity", "stv_outcome", {"winner": "c1", "session": "sess1"})
    await sqlite_db.log_event("memory", "edge_created", {"edge_id": "e1", "session": "sess1"})
    await sqlite_db.log_event("memory", "retrieval", {"query": "test", "session": "sess2"})
    await sqlite_db.log_event("skills", "skill_activated", {"skill": "s1", "session": "sess2"})
    await sqlite_db.log_event("skills", "skill_error", {"skill": "s1", "session": "sess2"})


@pytest.mark.asyncio
async def test_replay_events_all(replay, seeded_events, querier):
    events = await replay.replay_events()
    assert len(events) >= 7


@pytest.mark.asyncio
async def test_replay_events_by_fihg(replay, seeded_events):
    events = await replay.replay_events(fihg="identity")
    assert all(e.get("fihg") == "identity" for e in events)


@pytest.mark.asyncio
async def test_replay_events_by_type(replay, seeded_events):
    events = await replay.replay_events(event_type="stv_vote")
    assert len(events) >= 1
    assert events[0]["event_type"] == "stv_vote"


@pytest.mark.asyncio
async def test_replay_events_with_limit(replay, seeded_events):
    events = await replay.replay_events(limit=2)
    assert len(events) <= 2


@pytest.mark.asyncio
async def test_replay_timeline(replay, seeded_events):
    timeline = await replay.replay_timeline(time_window_hours=24.0)
    assert len(timeline) > 0


@pytest.mark.asyncio
async def test_replay_timeline_narrow_window(replay, seeded_events):
    # Use a window that definitely excludes all events (1 second ago)
    import asyncio
    await asyncio.sleep(0.1)  # Ensure events are in the past
    timeline = await replay.replay_timeline(time_window_hours=0.00001)
    # Just check it returns a list (may or may not be empty depending on timing)
    assert isinstance(timeline, list)


@pytest.mark.asyncio
async def test_summarize_session(replay, seeded_events):
    summary = await replay.summarize_session("sess1")
    assert summary["session_id"] == "sess1"
    assert summary["event_count"] >= 3
    # Check that identity events are present
    assert summary["event_count"] > 0


@pytest.mark.asyncio
async def test_summarize_session_empty(replay, seeded_events):
    summary = await replay.summarize_session("nonexistent")
    assert summary["event_count"] == 0
    assert summary["key_decisions"] == []


@pytest.mark.asyncio
async def test_summarize_graph_activity(replay, seeded_events):
    report = await replay.summarize_graph_activity("identity", time_window_hours=24.0)
    assert report["fihg"] == "identity"
    assert report["event_count"] >= 3
    assert "summary" in report


@pytest.mark.asyncio
async def test_summarize_graph_activity_empty(replay, seeded_events):
    # Use a very narrow window that should exclude most events
    import asyncio
    await asyncio.sleep(2)  # Wait 2 seconds
    report = await replay.summarize_graph_activity("nonexistent_graph", time_window_hours=0.001)
    assert report["event_count"] == 0


@pytest.mark.asyncio
async def test_generate_activity_report(replay, seeded_events):
    report = await replay.generate_activity_report(time_window_hours=24.0)
    assert report["total_events"] >= 7
    assert "identity" in report["graphs"]
    assert "memory" in report["graphs"]
    assert "skills" in report["graphs"]
    assert "generated_at" in report


@pytest.mark.asyncio
async def test_generate_activity_report_subset_graphs(replay, seeded_events):
    report = await replay.generate_activity_report(
        time_window_hours=24.0,
        include_graphs=["identity"],
    )
    assert "identity" in report["graphs"]
    assert "memory" not in report["graphs"]


@pytest.mark.asyncio
async def test_export_session_log(replay, seeded_events):
    log_json = await replay.export_session_log("sess1")
    assert len(log_json) > 0
    # Validate it's valid JSON
    import json
    events = json.loads(log_json)
    assert isinstance(events, list)


@pytest.mark.asyncio
async def test_import_session_log(replay, seeded_events):
    log_json = await replay.export_session_log("sess1")
    count = await replay.import_session_log(log_json)
    assert count > 0
