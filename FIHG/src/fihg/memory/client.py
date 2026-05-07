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
        """Update freshness based on time since last access using DecayEngine."""
        from ...core.decay import DecayEngine
        from ...core.base import BaseNode
        from datetime import datetime

        # Fetch node properties from graph
        result = await self.graph.execute(
            "g.V(:id).valueMap(true)",
            {"id": node_id}
        )
        if not result:
            return
        props = result[0]

        # Parse timestamps
        last_used = props.get("last_used_at")
        if last_used:
            if isinstance(last_used, str):
                last_used_dt = datetime.fromisoformat(last_used)
            else:
                last_used_dt = last_used
        else:
            last_used_dt = None

        created = props.get("created_at")
        if created:
            if isinstance(created, str):
                created_dt = datetime.fromisoformat(created)
            else:
                created_dt = created
        else:
            created_dt = datetime.utcnow()

        # Build BaseNode object
        node = BaseNode(
            id=node_id,
            type=props.get("type", "memory"),
            label=props.get("label", ""),
            freshness=float(props.get("freshness", 1.0)),
            last_used_at=last_used_dt,
            created_at=created_dt,
            visibility=props.get("visibility", True),
            confidence=props.get("confidence", 0.5),
            wear=props.get("wear", 0.0),
            activity_count=props.get("activity_count", 0),
            error_count=props.get("error_count", 0),
            success_rate=props.get("success_rate", 1.0),
            version=props.get("version", 1),
        )

        # Apply decay
        engine = DecayEngine(default_decay_rate=decay_rate)
        engine.decay_node_freshness(node)

        # Persist updated freshness
        await self.graph.execute(
            "g.V(:id).property('freshness', :freshness)",
            {"id": node_id, "freshness": node.freshness}
        )