"""Identity FIHG client"""

from typing import Optional
from ...db.arcadedb import ArcadeDBClient


class IdentityFIHGClient:
    """Client for Identity FIHG graph operations"""
    
    def __init__(self, graph_client: ArcadeDBClient):
        self.graph = graph_client
    
    async def create_persona(self, name: str, properties: dict) -> dict:
        """Create a persona node"""
        return await self.graph.create_vertex("persona", {"name": name, **properties})
    
    async def create_policy(self, name: str, priority: int, 
                           conditions: list[str] = None) -> dict:
        """Create a policy node"""
        props = {"name": name, "priority": priority}
        if conditions:
            props["conditions"] = ",".join(conditions)
        return await self.graph.create_vertex("policy", props)
    
    async def create_style_rule(self, name: str, blocks: str = None,
                               prioritizes: str = None) -> dict:
        """Create a style rule with relationships"""
        rule = await self.graph.create_vertex("style", {"name": name})
        
        if blocks:
            # Find the node to block and create edge
            target = await self.graph.find_vertex("style", "name", blocks)
            if target:
                await self.graph.create_edge(rule["id"], target[0]["id"], "blocks")
        
        return rule
    
    async def create_delegation_slot(self, slot_name: str, 
                                    agent_type: str) -> dict:
        """Create a delegation slot for agent dispatch"""
        return await self.graph.create_vertex("delegation_slot", {
            "name": slot_name,
            "agent_type": agent_type,
            "status": "available"
        })
    
    async def add_policy_vote(self, task_id: str, candidate_id: str,
                             rank: int, voter_type: str, 
                             weight: float, rationale: str) -> dict:
        """Record a policy vote"""
        return await self.graph.create_vertex("policy_vote", {
            "task_id": task_id,
            "candidate_id": candidate_id,
            "rank": rank,
            "voter_type": voter_type,
            "weight": weight,
            "rationale": rationale
        })