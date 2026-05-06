"""Core module - shared primitives and cross-graph bridges"""

from .base import BaseNode, BaseEdge, BaseHyperedge, GraphState
from .bridges import (
    BridgeResult,
    IdentityMemoryBridge,
    IdentitySkillsBridge,
    MemorySkillsBridge,
    CrossGraphTraversal,
    CrossGraphBridgeManager,
)
from .metrics import (
    aggregate_fihg_metrics,
    get_skill_activation_stats,
    get_memory_retrieval_stats,
    get_identity_confidence_stats,
)

__all__ = [
    "BaseNode",
    "BaseEdge",
    "BaseHyperedge",
    "GraphState",
    "BridgeResult",
    "IdentityMemoryBridge",
    "IdentitySkillsBridge",
    "MemorySkillsBridge",
    "CrossGraphTraversal",
    "CrossGraphBridgeManager",
    "aggregate_fihg_metrics",
    "get_skill_activation_stats",
    "get_memory_retrieval_stats",
    "get_identity_confidence_stats",
]