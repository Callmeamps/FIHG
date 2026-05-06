"""Tests for SessionStateManager"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta

from src.db.sqlite_schema import SQLiteSchema
from src.db.session_state import SessionStateManager


@pytest.fixture
async def sqlite_db():
    """Create an in-memory SQLite database with schema."""
    db = SQLiteSchema(":memory:")
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def manager(sqlite_db):
    return SessionStateManager(sqlite_db)


@pytest.mark.asyncio
async def test_save_and_load_state(manager):
    await manager.save_state(
        "sess1",
        identity_state={"active_claim": "c1"},
        memory_state={"last_context": "ctx1"},
        skills_state={"active_skill": "summarize"},
    )
    state = await manager.load_state("sess1")
    assert state is not None
    assert state["identity_state"] == {"active_claim": "c1"}
    assert state["memory_state"] == {"last_context": "ctx1"}
    assert state["skills_state"] == {"active_skill": "summarize"}


@pytest.mark.asyncio
async def test_load_nonexistent_session(manager):
    state = await manager.load_state("no_such_session")
    assert state is None


@pytest.mark.asyncio
async def test_update_state_identity(manager):
    await manager.save_state("sess1", identity_state={"key1": "val1"})
    await manager.update_state("sess1", "identity", "key2", "val2")
    state = await manager.load_state("sess1")
    assert state["identity_state"]["key1"] == "val1"
    assert state["identity_state"]["key2"] == "val2"


@pytest.mark.asyncio
async def test_update_state_memory(manager):
    await manager.save_state("sess1", memory_state={"facts": ["a", "b"]})
    await manager.update_state("sess1", "memory", "facts", ["a", "b", "c"])
    state = await manager.load_state("sess1")
    assert state["memory_state"]["facts"] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_update_state_skills(manager):
    await manager.save_state("sess1")
    await manager.update_state("sess1", "skills", "routing_table", {"default": "identity"})
    state = await manager.load_state("sess1")
    assert state["skills_state"]["routing_table"] == {"default": "identity"}


@pytest.mark.asyncio
async def test_update_state_invalid_graph(manager):
    await manager.save_state("sess1")
    with pytest.raises(ValueError, match="Unknown graph"):
        await manager.update_state("sess1", "bogus", "key", "val")


@pytest.mark.asyncio
async def test_clear_state(manager):
    await manager.save_state("sess1", identity_state={"x": 1})
    result = await manager.clear_state("sess1")
    assert result is True
    state = await manager.load_state("sess1")
    assert state is None


@pytest.mark.asyncio
async def test_clear_nonexistent_session(manager):
    result = await manager.clear_state("no_such_session")
    assert result is False


@pytest.mark.asyncio
async def test_list_sessions(manager):
    await manager.save_state("sess1", identity_state={})
    await manager.save_state("sess2", identity_state={})
    sessions = await manager.list_sessions()
    # Both sessions exist, ordering may vary within same second
    assert set(sessions) == {"sess1", "sess2"}
    assert len(sessions) == 2


@pytest.mark.asyncio
async def test_get_graph_state(manager):
    await manager.save_state(
        "sess1",
        identity_state={"claim": "c1"},
        memory_state={"episode": "e1"},
    )
    identity = await manager.get_graph_state("sess1", "identity")
    assert identity == {"claim": "c1"}

    memory = await manager.get_graph_state("sess1", "memory")
    assert memory == {"episode": "e1"}

    skills = await manager.get_graph_state("sess1", "skills")
    assert skills == {}


@pytest.mark.asyncio
async def test_get_graph_state_nonexistent_session(manager):
    state = await manager.get_graph_state("no_session", "identity")
    assert state is None


@pytest.mark.asyncio
async def test_get_graph_state_invalid_graph(manager):
    await manager.save_state("sess1")
    with pytest.raises(ValueError, match="Unknown graph"):
        await manager.get_graph_state("sess1", "bogus")


@pytest.mark.asyncio
async def test_get_session_age(manager):
    await manager.save_state("sess1", identity_state={})
    age = await manager.get_session_age("sess1")
    assert age is not None
    assert age < 1.0  # Should be less than 1 second old


@pytest.mark.asyncio
async def test_get_session_age_nonexistent(manager):
    age = await manager.get_session_age("no_session")
    assert age is None


@pytest.mark.asyncio
async def test_prune_stale_sessions(manager):
    await manager.save_state("fresh", identity_state={})
    # Manually insert a stale session
    conn = manager.db._db
    stale_time = (datetime.now() - timedelta(hours=48)).isoformat()
    await conn.execute(
        "INSERT INTO session_state (session_id, last_identity_state, updated_at) VALUES (?, ?, ?)",
        ("stale", "{}", stale_time),
    )
    await conn.commit()

    pruned = await manager.prune_stale_sessions(max_age_seconds=86400)
    assert pruned == 1

    sessions = await manager.list_sessions()
    assert "fresh" in sessions
    assert "stale" not in sessions


@pytest.mark.asyncio
async def test_prune_no_stale_sessions(manager):
    await manager.save_state("sess1", identity_state={})
    pruned = await manager.prune_stale_sessions(max_age_seconds=86400)
    assert pruned == 0
