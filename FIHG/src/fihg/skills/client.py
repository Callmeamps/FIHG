"""Skills FIHG client"""

from typing import Optional
from datetime import datetime
from ...db.arcadedb import ArcadeDBClient


class SkillsFIHGClient:
    """Client for Skills FIHG graph operations"""
    
    def __init__(self, graph_client: ArcadeDBClient):
        self.graph = graph_client
    
    async def create_skill(self, name: str, category: str,
                          confidence: float = 0.5) -> dict:
        """Create a skill node"""
        return await self.graph.create_vertex("skill", {
            "name": name,
            "category": category,
            "confidence": confidence,
            "evidence_count": 0,
            "last_practiced_at": datetime.utcnow().isoformat(),
            "decay": 0.0
        })
    
    async def add_skill_dependency(self, skill_id: str, depends_on_id: str,
                                  strength: float = 1.0) -> dict:
        """Add a dependency edge between skills"""
        return await self.graph.create_edge(skill_id, depends_on_id, "depends_on", {
            "strength": strength
        })
    
    async def add_skill_transfer(self, from_skill_id: str, to_skill_id: str,
                                strength: float = 0.5) -> dict:
        """Add a transfer edge (skill transfers to another)"""
        return await self.graph.create_edge(from_skill_id, to_skill_id, "transfers_to", {
            "strength": strength
        })
    
    async def record_benchmark(self, skill_id: str, task_id: str,
                              score: float, notes: str = None) -> dict:
        """Record a benchmark for a skill"""
        return await self.graph.create_vertex("skill_benchmark", {
            "skill_id": skill_id,
            "task_id": task_id,
            "score": score,
            "notes": notes,
            "date": datetime.utcnow().isoformat()
        })
    
    async def update_skill_confidence(self, skill_id: str,
                                     success: bool, latency: float = None):
        """Update skill confidence based on execution result.
        
        - Increases confidence by +0.05 on success
        - Decreases by -0.1 on failure
        - Updates last_practiced_at to now
        """
        from datetime import datetime
        # Fetch current confidence
        result = await self.graph.execute(
            "g.V(:id).valueMap(true)",
            {"id": skill_id}
        )
        if not result:
            return
        props = result[0]
        current_conf = float(props.get("confidence", 0.5))
        
        delta = 0.05 if success else -0.1
        new_conf = max(0.0, min(1.0, current_conf + delta))
        
        # Update confidence and last_practiced_at atomically
        await self.graph.execute(
            "g.V(:skill_id).property('confidence', :confidence).property('last_practiced_at', :timestamp)",
            {
                "skill_id": skill_id,
                "confidence": new_conf,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    async def get_skill_dependencies(self, skill_name: str) -> list[dict]:
        """Get all dependencies of a skill"""
        # Traverse depends_on edges
        pass