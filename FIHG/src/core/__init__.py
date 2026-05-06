"""Core module - shared primitives and cross-graph bridges"""

from .base import BaseNode, BaseEdge, BaseHyperedge, GraphState
from .hyperedges import HyperedgeManager
from .decay import DecayEngine
from .replay import ReplayEngine
from .subgraphs import SubgraphManager, Subgraph
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
    "HyperedgeManager",
    "DecayEngine",
    "ReplayEngine",
    "SubgraphManager",
    "Subgraph",
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
