"""Recursive subgraph support for FIHG graphs"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field, ConfigDict


class Subgraph(BaseModel):
    """A recursive subgraph within a parent FIHG graph."""
    id: str = Field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:8]}")
    name: str
    parent_graph: str
    node_ids: Set[str] = Field(default_factory=set)
    edge_ids: Set[str] = Field(default_factory=set)
    hyperedge_ids: Set[str] = Field(default_factory=set)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state: str = "active"  # active, archived, deleted

    model_config = ConfigDict(json_encoders={set: list})


class SubgraphManager:
    """Manage recursive subgraphs within FIHG graphs.

    Supports nested subgraphs (subgraphs within subgraphs),
    entity membership tracking, and subgraph lifecycle operations.
    """

    def __init__(self, sqlite_db, arcedb_clients: Optional[Dict[str, Any]] = None):
        self.db = sqlite_db
        self.arcedb = arcedb_clients or {}
        self._subgraphs: Dict[str, Subgraph] = {}

    async def create_subgraph(
        self,
        name: str,
        parent_graph: str,
        node_ids: Optional[List[str]] = None,
        edge_ids: Optional[List[str]] = None,
        hyperedge_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Subgraph:
        """Create a new subgraph within a parent graph."""
        subgraph = Subgraph(
            name=name,
            parent_graph=parent_graph,
            node_ids=set(node_ids or []),
            edge_ids=set(edge_ids or []),
            hyperedge_ids=set(hyperedge_ids or []),
            metadata=metadata or {},
        )
        self._subgraphs[subgraph.id] = subgraph

        await self.db.log_event(
            parent_graph,
            "subgraph_created",
            {
                "subgraph_id": subgraph.id,
                "name": subgraph.name,
                "node_count": len(subgraph.node_ids),
                "edge_count": len(subgraph.edge_ids),
                "hyperedge_count": len(subgraph.hyperedge_ids),
                "metadata": subgraph.metadata,
            },
        )
        return subgraph

    async def get_subgraph(self, subgraph_id: str) -> Optional[Subgraph]:
        """Retrieve a subgraph by ID."""
        return self._subgraphs.get(subgraph_id)

    async def list_subgraphs(
        self,
        parent_graph: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[Subgraph]:
        """List subgraphs with optional filters."""
        subs = list(self._subgraphs.values())
        if parent_graph:
            subs = [s for s in subs if s.parent_graph == parent_graph]
        if state:
            subs = [s for s in subs if s.state == state]
        return subs

    async def add_nodes(self, subgraph_id: str, node_ids: List[str]) -> bool:
        """Add nodes to a subgraph."""
        sub = self._subgraphs.get(subgraph_id)
        if not sub:
            return False
        sub.node_ids.update(node_ids)
        await self.db.log_event(
            sub.parent_graph,
            "subgraph_nodes_added",
            {"subgraph_id": subgraph_id, "node_ids": node_ids},
        )
        return True

    async def remove_nodes(self, subgraph_id: str, node_ids: List[str]) -> bool:
        """Remove nodes from a subgraph."""
        sub = self._subgraphs.get(subgraph_id)
        if not sub:
            return False
        sub.node_ids.difference_update(node_ids)
        await self.db.log_event(
            sub.parent_graph,
            "subgraph_nodes_removed",
            {"subgraph_id": subgraph_id, "node_ids": node_ids},
        )
        return True

    async def add_edges(self, subgraph_id: str, edge_ids: List[str]) -> bool:
        """Add edges to a subgraph."""
        sub = self._subgraphs.get(subgraph_id)
        if not sub:
            return False
        sub.edge_ids.update(edge_ids)
        return True

    async def add_hyperedges(self, subgraph_id: str, hyperedge_ids: List[str]) -> bool:
        """Add hyperedges to a subgraph."""
        sub = self._subgraphs.get(subgraph_id)
        if not sub:
            return False
        sub.hyperedge_ids.update(hyperedge_ids)
        return True

    async def archive_subgraph(self, subgraph_id: str) -> bool:
        """Archive a subgraph (soft delete)."""
        sub = self._subgraphs.get(subgraph_id)
        if not sub:
            return False
        sub.state = "archived"
        await self.db.log_event(
            sub.parent_graph,
            "subgraph_archived",
            {"subgraph_id": subgraph_id},
        )
        return True

    async def delete_subgraph(self, subgraph_id: str) -> bool:
        """Permanently delete a subgraph."""
        sub = self._subgraphs.get(subgraph_id)
        if not sub:
            return False
        parent = sub.parent_graph
        del self._subgraphs[subgraph_id]
        await self.db.log_event(
            parent,
            "subgraph_deleted",
            {"subgraph_id": subgraph_id},
        )
        return True

    async def get_subgraph_stats(self, subgraph_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a subgraph."""
        sub = self._subgraphs.get(subgraph_id)
        if not sub:
            return None
        return {
            "id": sub.id,
            "name": sub.name,
            "parent_graph": sub.parent_graph,
            "node_count": len(sub.node_ids),
            "edge_count": len(sub.edge_ids),
            "hyperedge_count": len(sub.hyperedge_ids),
            "state": sub.state,
            "created_at": sub.created_at.isoformat(),
            "metadata": sub.metadata,
        }

    async def find_subgraph_containing(self, entity_id: str) -> Optional[Subgraph]:
        """Find the first subgraph containing a given entity."""
        for sub in self._subgraphs.values():
            if (
                entity_id in sub.node_ids
                or entity_id in sub.edge_ids
                or entity_id in sub.hyperedge_ids
            ):
                return sub
        return None

    async def merge_subgraphs(
        self,
        source_id: str,
        target_id: str,
        new_name: Optional[str] = None,
    ) -> Optional[Subgraph]:
        """Merge source subgraph into target subgraph."""
        source = self._subgraphs.get(source_id)
        target = self._subgraphs.get(target_id)
        if not source or not target:
            return None
        if source.parent_graph != target.parent_graph:
            raise ValueError("Cannot merge subgraphs from different parent graphs")

        target.node_ids.update(source.node_ids)
        target.edge_ids.update(source.edge_ids)
        target.hyperedge_ids.update(source.hyperedge_ids)
        target.metadata.update(source.metadata)
        if new_name:
            target.name = new_name

        await self.archive_subgraph(source_id)
        await self.db.log_event(
            target.parent_graph,
            "subgraphs_merged",
            {"source_id": source_id, "target_id": target_id},
        )
        return target
