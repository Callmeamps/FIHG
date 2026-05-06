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
]