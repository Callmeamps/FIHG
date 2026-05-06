"""Tests for SubgraphManager"""

import pytest
import asyncio
from datetime import datetime, timezone

from src.db.sqlite_schema import SQLiteSchema
from src.core.subgraphs import SubgraphManager, Subgraph


@pytest.fixture
async def sqlite_db():
    db = SQLiteSchema(":memory:")
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def manager(sqlite_db):
    return SubgraphManager(sqlite_db)


@pytest.fixture
async def seeded_subgraphs(manager):
    """Seed subgraphs for testing."""
    sg1 = await manager.create_subgraph(
        name="cluster_a",
        parent_graph="identity",
        node_ids=["n1", "n2", "n3"],
        edge_ids=["e1"],
        metadata={"purpose": "test"},
    )
    sg2 = await manager.create_subgraph(
        name="cluster_b",
        parent_graph="identity",
        node_ids=["n4", "n5"],
        edge_ids=["e2", "e3"],
        metadata={"purpose": "test"},
    )
    sg3 = await manager.create_subgraph(
        name="mem_cluster",
        parent_graph="memory",
        node_ids=["m1", "m2"],
        hyperedge_ids=["he1"],
    )
    return sg1, sg2, sg3


@pytest.mark.asyncio
async def test_create_subgraph(manager):
    sg = await manager.create_subgraph(
        name="test_sub",
        parent_graph="identity",
        node_ids=["n1"],
        metadata={"test": True},
    )
    assert sg.id.startswith("sub_")
    assert sg.name == "test_sub"
    assert sg.parent_graph == "identity"
    assert sg.node_ids == {"n1"}


@pytest.mark.asyncio
async def test_get_subgraph(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    retrieved = await manager.get_subgraph(sg1.id)
    assert retrieved is not None
    assert retrieved.id == sg1.id
    assert retrieved.name == "cluster_a"


@pytest.mark.asyncio
async def test_get_nonexistent_subgraph(manager):
    result = await manager.get_subgraph("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_subgraphs_all(manager, seeded_subgraphs):
    subs = await manager.list_subgraphs()
    assert len(subs) == 3


@pytest.mark.asyncio
async def test_list_subgraphs_by_parent(manager, seeded_subgraphs):
    subs = await manager.list_subgraphs(parent_graph="identity")
    assert len(subs) == 2
    assert all(s.parent_graph == "identity" for s in subs)


@pytest.mark.asyncio
async def test_list_subgraphs_by_state(manager, seeded_subgraphs):
    subs = await manager.list_subgraphs(state="active")
    assert len(subs) == 3


@pytest.mark.asyncio
async def test_add_nodes(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    assert len(sg1.node_ids) == 3
    await manager.add_nodes(sg1.id, ["n10", "n11"])
    updated = await manager.get_subgraph(sg1.id)
    assert len(updated.node_ids) == 5
    assert "n10" in updated.node_ids


@pytest.mark.asyncio
async def test_remove_nodes(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    await manager.remove_nodes(sg1.id, ["n1", "n2"])
    updated = await manager.get_subgraph(sg1.id)
    assert "n1" not in updated.node_ids
    assert "n3" in updated.node_ids


@pytest.mark.asyncio
async def test_add_edges(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    await manager.add_edges(sg1.id, ["e10", "e11"])
    updated = await manager.get_subgraph(sg1.id)
    assert len(updated.edge_ids) == 3


@pytest.mark.asyncio
async def test_add_hyperedges(manager, seeded_subgraphs):
    sg3 = seeded_subgraphs[2]
    await manager.add_hyperedges(sg3.id, ["he2", "he3"])
    updated = await manager.get_subgraph(sg3.id)
    assert len(updated.hyperedge_ids) == 3


@pytest.mark.asyncio
async def test_archive_subgraph(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    await manager.archive_subgraph(sg1.id)
    archived = await manager.get_subgraph(sg1.id)
    assert archived.state == "archived"

    active = await manager.list_subgraphs(state="active")
    assert sg1 not in active


@pytest.mark.asyncio
async def test_delete_subgraph(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    result = await manager.delete_subgraph(sg1.id)
    assert result is True
    deleted = await manager.get_subgraph(sg1.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_nonexistent_subgraph(manager):
    result = await manager.delete_subgraph("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_get_subgraph_stats(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    stats = await manager.get_subgraph_stats(sg1.id)
    assert stats is not None
    assert stats["name"] == "cluster_a"
    assert stats["node_count"] == 3
    assert stats["edge_count"] == 1
    assert stats["state"] == "active"


@pytest.mark.asyncio
async def test_get_subgraph_stats_nonexistent(manager):
    stats = await manager.get_subgraph_stats("nonexistent")
    assert stats is None


@pytest.mark.asyncio
async def test_find_subgraph_containing_node(manager, seeded_subgraphs):
    sg = await manager.find_subgraph_containing("n1")
    assert sg is not None
    assert sg.name == "cluster_a"


@pytest.mark.asyncio
async def test_find_subgraph_containing_edge(manager, seeded_subgraphs):
    sg = await manager.find_subgraph_containing("e1")
    assert sg is not None
    assert sg.name == "cluster_a"


@pytest.mark.asyncio
async def test_find_subgraph_not_found(manager, seeded_subgraphs):
    sg = await manager.find_subgraph_containing("nonexistent")
    assert sg is None


@pytest.mark.asyncio
async def test_merge_subgraphs(manager, seeded_subgraphs):
    sg1, sg2, _ = seeded_subgraphs
    merged = await manager.merge_subgraphs(sg2.id, sg1.id, new_name="merged_cluster")

    assert merged is not None
    assert merged.name == "merged_cluster"
    # sg1 had n1,n2,n3; sg2 had n4,n5
    assert len(merged.node_ids) == 5
    # sg1 had e1; sg2 had e2,e3
    assert len(merged.edge_ids) == 3

    # Source should be archived
    archived = await manager.get_subgraph(sg2.id)
    assert archived.state == "archived"


@pytest.mark.asyncio
async def test_merge_subgraphs_different_parents(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]  # identity
    sg3 = seeded_subgraphs[2]  # memory
    with pytest.raises(ValueError, match="Cannot merge subgraphs from different parent graphs"):
        await manager.merge_subgraphs(sg3.id, sg1.id)


@pytest.mark.asyncio
async def test_merge_nonexistent_source(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    result = await manager.merge_subgraphs("nonexistent", sg1.id)
    assert result is None


@pytest.mark.asyncio
async def test_subgraph_json_serialization(manager, seeded_subgraphs):
    sg1 = seeded_subgraphs[0]
    json_data = sg1.model_dump_json()
    assert len(json_data) > 0
    assert "cluster_a" in json_data
