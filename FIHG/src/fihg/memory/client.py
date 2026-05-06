"""Memory FIHG client"""

from typing import Optional
from datetime import datetime
from ...db.arcadedb import ArcadeDBClient


class MemoryFIHGClient:
    """Client for Memory FIHG graph operations"""
    
    def __init__(self, graph_client: ArcadeDBClient):
        self.graph = graph_client
    
    async def create_episode(self, event_type: str, participants: list[str],
                            properties: dict = None) -> dict:
        """Create an episode (conversation or action)"""
        props = {
            "event_type": event_type,
            "participants": ",".join(participants),
            "timestamp": datetime.utcnow().isoformat(),
            **(properties or {})
        }
        return await self.graph.create_vertex("episode", props)
    
    async def create_fact(self, subject: str, predicate: str, 
                         object: str, source: str = None,
                         trust: float = 0.5) -> dict:
        """Create a fact (semantic memory)"""
        props = {
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "trust": trust
        }
        if source:
            props["source"] = source
        return await self.graph.create_vertex("fact", props)
    
    async def create_preference(self, entity: str, preference: str,
                               strength: float = 0.5) -> dict:
        """Create a preference memory"""
        return await self.graph.create_vertex("preference", {
            "entity": entity,
            "preference": preference,
            "strength": strength,
            "created_at": datetime.utcnow().isoformat()
        })
    
    async def create_summary(self, content: str, 
                            linked_episodes: list[str] = None) -> dict:
        """Create a summary node linked to episodes"""
        summary = await self.graph.create_vertex("summary", {
            "content": content,
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Link to episodes
        if linked_episodes:
            for episode_id in linked_episodes:
                await self.graph.create_edge(summary["id"], episode_id, "summarizes")
        
        return summary
    
    async def record_contradiction(self, fact_a_id: str, fact_b_id: str,
                                  resolution: str = None) -> dict:
        """Record a contradiction between two facts"""
        return await self.graph.create_vertex("contradiction", {
            "fact_a": fact_a_id,
            "fact_b": fact_b_id,
            "resolution": resolution,
            "created_at": datetime.utcnow().isoformat()
        })
    
    async def update_memory_freshness(self, node_id: str, decay_rate: float = 0.1):
        """Update freshness based on time since last access"""
        # This would be implemented with a decay function
        pass