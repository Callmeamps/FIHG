"""Core base classes for FIHG nodes, edges, and hyperedges"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class BaseNode(BaseModel):
    """Shared primitive for all FIHG nodes"""
    id: str
    type: str
    label: str
    state: str = "active"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    freshness: float = Field(default=1.0, ge=0.0, le=1.0)  # 1.0 = freshest
    wear: float = Field(default=0.0, ge=0.0, le=1.0)  # 0.0 = pristine
    visibility: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    activity_count: int = 0
    error_count: int = 0
    success_rate: float = 1.0


class BaseEdge(BaseModel):
    """Shared primitive for all FIHG edges"""
    id: str
    source: str  # source node id
    target: str  # target node id
    relation: str
    weight: float = 1.0
    direction: str = "outgoing"  # outgoing, incoming, bidirectional
    created_at: datetime = Field(default_factory=datetime.utcnow)
    wear: float = 0.0
    clarity: float = 1.0  # for graphs (brightness)
    activation_count: int = 0
    evidence: list[str] = Field(default_factory=list)


class BaseHyperedge(BaseModel):
    """Hyperedge modeled as vertex with participant links"""
    id: str
    participants: list[str]  # node ids
    role_map: dict[str, str] = Field(default_factory=dict)  # node_id -> role
    event_type: str
    score_vector: dict[str, float] = Field(default_factory=dict)
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    provenance: str = ""  # source or origin
    outcome: str = ""
    runner_ups: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GraphState:
    """Track live state signals for nodes and edges"""
    
    @staticmethod
    def calculate_brightness(activity_count: int, success_rate: float, 
                            last_used: Optional[datetime], decay_rate: float) -> float:
        """Calculate brightness (0.0 to 1.0) for graph entities"""
        if activity_count == 0:
            return 0.5  # default brightness for unused
        
        # Base brightness from activity
        base = min(activity_count / 100.0, 1.0)  # normalize to 100
        
        # Adjust for success rate
        adjusted = base * success_rate
        
        # Decay based on time since last use
        if last_used:
            hours_since = (datetime.utcnow() - last_used).total_seconds() / 3600
            decay = min(hours_since / 24.0 * decay_rate, 0.5)  # max 50% decay per day
            adjusted *= (1.0 - decay)
        
        return max(0.0, min(1.0, adjusted))
    
    @staticmethod
    def calculate_wear(activity_count: int, error_count: int) -> float:
        """Calculate wear (0.0 = pristine, 1.0 = worn out)"""
        if activity_count == 0:
            return 0.0
        
        error_ratio = error_count / activity_count
        activity_factor = min(activity_count / 1000.0, 1.0)  # normalize to 1000
        
        return min(error_ratio * activity_factor, 1.0)