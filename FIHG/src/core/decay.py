"""Decay and wear scoring for FIHG nodes and edges"""

import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from ..core.base import BaseNode, BaseEdge


class DecayEngine:
    """Automated time-based decay and wear scoring for FIHG entities."""

    def __init__(
        self,
        default_decay_rate: float = 0.05,
        wear_error_weight: float = 0.7,
        wear_activity_weight: float = 0.3,
        freshness_half_life_hours: float = 24.0,
    ):
        self.default_decay_rate = default_decay_rate
        self.wear_error_weight = wear_error_weight
        self.wear_activity_weight = wear_activity_weight
        self.freshness_half_life_hours = freshness_half_life_hours

    # ── Node methods ──

    def decay_node_freshness(self, node: BaseNode, now: Optional[datetime] = None) -> float:
        """Apply time-based freshness decay to a node."""
        now = now or datetime.now(timezone.utc)
        last_used = node.last_used_at or node.created_at
        if last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=timezone.utc)

        hours_since = (now - last_used).total_seconds() / 3600.0
        decay = 0.5 ** (hours_since / self.freshness_half_life_hours)
        node.freshness = max(0.0, min(1.0, node.freshness * decay))
        return node.freshness

    def calculate_node_wear(self, node: BaseNode) -> float:
        """Calculate wear score for a node (0.0 = pristine, 1.0 = worn)."""
        if node.activity_count == 0:
            node.wear = 0.0
            return 0.0

        error_ratio = node.error_count / max(node.activity_count, 1)
        error_wear = error_ratio * self.wear_error_weight
        activity_wear = math.log1p(node.activity_count) / math.log1p(10000) * self.wear_activity_weight
        node.wear = min(1.0, error_wear + activity_wear)
        return node.wear

    def decay_node(self, node: BaseNode, now: Optional[datetime] = None) -> Dict[str, float]:
        """Full decay cycle for a node."""
        freshness = self.decay_node_freshness(node, now)
        wear = self.calculate_node_wear(node)

        if node.activity_count > 0:
            wear_penalty = wear * 0.1
            node.success_rate = max(0.0, node.success_rate - wear_penalty)

        return {"freshness": freshness, "wear": wear, "success_rate": node.success_rate}

    # ── Edge methods ──

    def decay_edge_clarity(self, edge: BaseEdge, now: Optional[datetime] = None) -> float:
        """Apply time-based clarity decay to an edge (analogous to node freshness)."""
        now = now or datetime.now(timezone.utc)
        created = edge.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        hours_since = (now - created).total_seconds() / 3600.0
        decay = 0.5 ** (hours_since / self.freshness_half_life_hours)
        edge.clarity = max(0.0, min(1.0, edge.clarity * decay))
        return edge.clarity

    def calculate_edge_wear(self, edge: BaseEdge) -> float:
        """Calculate wear score for an edge."""
        if edge.activation_count == 0:
            edge.wear = 0.0
            return 0.0

        error_ratio = len(edge.evidence) / max(edge.activation_count, 1)
        error_wear = error_ratio * self.wear_error_weight
        activity_wear = math.log1p(edge.activation_count) / math.log1p(10000) * self.wear_activity_weight
        edge.wear = min(1.0, error_wear + activity_wear)
        return edge.wear

    def decay_edge(self, edge: BaseEdge, now: Optional[datetime] = None) -> Dict[str, float]:
        """Full decay cycle for an edge."""
        clarity = self.decay_edge_clarity(edge, now)
        wear = self.calculate_edge_wear(edge)
        return {"clarity": clarity, "wear": wear}

    # ── Batch operations ──

    def batch_decay(
        self,
        nodes: List[BaseNode],
        edges: List[BaseEdge],
        now: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, float]]]:
        """Apply decay to a batch of nodes and edges."""
        return {
            "nodes": [self.decay_node(n, now) for n in nodes],
            "edges": [self.decay_edge(e, now) for e in edges],
        }

    def get_stale_entities(
        self,
        nodes: List[BaseNode],
        edges: List[BaseEdge],
        freshness_threshold: float = 0.1,
        now: Optional[datetime] = None,
    ) -> Dict[str, List[str]]:
        """Identify entities below freshness/clarity threshold."""
        stale_nodes = [n.id for n in nodes if self.decay_node_freshness(n, now) < freshness_threshold]
        stale_edges = [e.id for e in edges if self.decay_edge_clarity(e, now) < freshness_threshold]
        return {"stale_nodes": stale_nodes, "stale_edges": stale_edges}

    def get_worn_entities(
        self,
        nodes: List[BaseNode],
        edges: List[BaseEdge],
        wear_threshold: float = 0.8,
    ) -> Dict[str, List[str]]:
        """Identify entities above wear threshold."""
        worn_nodes = [n.id for n in nodes if self.calculate_node_wear(n) >= wear_threshold]
        worn_edges = [e.id for e in edges if self.calculate_edge_wear(e) >= wear_threshold]
        return {"worn_nodes": worn_nodes, "worn_edges": worn_edges}
