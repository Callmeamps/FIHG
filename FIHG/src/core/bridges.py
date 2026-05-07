"""Cross-graph bridges for FIHG traversals between Identity, Memory, and Skills graphs"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field

from ..db.arcadedb import ArcadeDBClient, FIHGGraphManager
from ..core.base import BaseNode, BaseEdge

# Gremlin query templates for parameterized execution

STYLE_QUERY: str = "g.V().has('style', 'id', :style_id)"

STYLE_EPISODES_QUERY: str = """
g.V().has('style', 'id', :style_id).as('s')
  .V().has('episode', 'event_type', within('conversation', 'interaction'))
  .has('style_used', s.name)
  .order().by('timestamp', decr)
  .limit(:limit)
"""

STYLE_FACTS_QUERY: str = """
g.V().has('fact', 'predicate', 'response_style_preference')
  .has('object', :style_name)
  .limit(:limit)
"""

PERSONA_BY_ID: str = "g.V().has('persona', 'id', :persona_id)"

PREFERENCES_QUERY: str = """
g.V().has('preference', 'entity', :persona_name)
  .order().by('strength', decr)
  .limit(:limit)
"""

DELEGATION_SLOT_BY_ID: str = "g.V().has('delegation_slot', 'id', :slot_id)"

SKILL_BY_NAME_PROJECT: str = """
g.V().has('skill', 'name', :skill_name)
  .project('id', 'name', 'category', 'confidence', 'evidence_count', 'decay')
  .by('id').by('name').by('category').by('confidence').by('evidence_count').by('decay')
"""

POLICY_BY_ID: str = "g.V().has('policy', 'id', :policy_id)"

SKILLS_BY_CATEGORY: str = """
g.V().has('skill', 'category', within(:categories))
  .order().by('confidence', decr)
"""

SKILL_BY_ID: str = "g.V().has('skill', 'id', :skill_id)"

EPISODE_BY_SKILL_NAME: str = """
g.V().has('skill_episode', 'skill_name', :skill_name)
  .has('success', 'True')
  .order().by('timestamp', decr)
  .limit(:limit)
"""

FACTS_BY_PREDICATE_OBJECT: str = """
g.V().has('fact', 'predicate', 'skill_example')
  .has('object', :skill_name)
  .limit(:limit)
"""

SKILL_EPISODE_COUNT: str = "g.V().has('skill_episode', 'skill_id', :skill_id).has('success', 'True').count()"

SKILL_FAILURE_COUNT: str = "g.V().has('skill_episode', 'skill_id', :skill_id).has('success', 'False').count()"

SKILL_UPDATE_CONFIDENCE: str = """
g.V().has('skill', 'id', :skill_id)
  .property('confidence', :confidence)
  .property('last_practiced_at', :timestamp)
"""

EXECUTED_SKILL_EDGE: str = """
g.V(:episode_id).addE('executed_skill').to(g.V(:skill_id))
  .property('outcome', :outcome)
  .property('timestamp', :timestamp)
"""


@dataclass
class BridgeResult:
    """Result from a cross-graph bridge operation"""
    source_graph: str
    target_graph: str
    source_id: str
    results: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class IdentityMemoryBridge:
    """Bridge between Identity and Memory graphs
    
    Enables:
    - Querying Memory for relevant past conversations when Identity selects a response style
    - Fetching user preferences to inform Identity decisions
    - Storing Identity decisions as memory episodes
    """
    
    def __init__(self, identity_graph: ArcadeDBClient, memory_graph: ArcadeDBClient):
        self.identity = identity_graph
        self.memory = memory_graph
    
    async def get_memory_for_response_style(self, style_id: str, limit: int = 10) -> BridgeResult:
        """Query Memory for relevant past conversations given an Identity response style
        
        Args:
            style_id: The response style selected by Identity
            limit: Maximum number of memory results
            
        Returns:
            BridgeResult with relevant episodes and facts
        """
        style_results = await self.identity.execute(STYLE_QUERY, {"style_id": style_id})
        
        if not style_results:
            return BridgeResult(
                source_graph="identity",
                target_graph="memory",
                source_id=style_id,
                metadata={"error": "Style not found"}
            )
        
        style_name = style_results[0].get("name", "") if style_results else ""
        
        episodes = await self.memory.execute(STYLE_EPISODES_QUERY, {"style_id": style_id, "limit": limit})
        
        facts = await self.memory.execute(STYLE_FACTS_QUERY, {"style_name": style_name, "limit": limit})
        
        return BridgeResult(
            source_graph="identity",
            target_graph="memory",
            source_id=style_id,
            results={
                "episodes": episodes,
                "facts": facts
            },
            metadata={
                "style_name": style_name,
                "episode_count": len(episodes),
                "fact_count": len(facts)
            }
        )
    
    async def get_memory_for_persona(self, persona_id: str, limit: int = 5) -> BridgeResult:
        """Query Memory for facts relevant to a persona
        
        Args:
            persona_id: The Identity persona to query for
            limit: Maximum results
            
        Returns:
            BridgeResult with relevant preferences and facts
        """
        persona_results = await self.identity.execute(PERSONA_BY_ID, {"persona_id": persona_id})
        
        if not persona_results:
            return BridgeResult(
                source_graph="identity",
                target_graph="memory",
                source_id=persona_id,
                metadata={"error": "Persona not found"}
            )
        
        persona_name = persona_results[0].get("name", "")
        
        preferences = await self.memory.execute(PREFERENCES_QUERY, {"persona_name": persona_name, "limit": limit})
        
        return BridgeResult(
            source_graph="identity",
            target_graph="memory",
            source_id=persona_id,
            results={"preferences": preferences},
            metadata={
                "persona_name": persona_name,
                "preference_count": len(preferences)
            }
        )
    
    async def store_decision_as_episode(self, decision: dict, context: dict = None) -> BridgeResult:
        """Store an Identity decision as a Memory episode
        
        Args:
            decision: The Identity decision (style, policy, agent dispatch)
            context: Additional context for the episode
            
        Returns:
            BridgeResult with the created episode
        """
        event_type = decision.get("type", "decision")
        participants = decision.get("participants", ["identity_system"])
        
        props = {
            "event_type": event_type,
            "participants": ",".join(participants),
            "timestamp": datetime.utcnow().isoformat(),
            "decision_type": decision.get("decision_type", "unknown"),
            "decision_id": decision.get("id", ""),
            "outcome": decision.get("outcome", ""),
        }
        
        if context:
            for key, value in context.items():
                props[f"context_{key}"] = str(value)
        
        query = "g.addV('decision_episode')"
        for key in props:
            query += f".property('{key}', :{key})"
        
        result = await self.memory.execute(query, props)
        
        return BridgeResult(
            source_graph="identity",
            target_graph="memory",
            source_id=decision.get("id", "unknown"),
            results=result,
            metadata={"event_type": event_type, "participants": participants}
        )


class IdentitySkillsBridge:
    """Bridge between Identity and Skills graphs
    
    Enables:
    - Querying Skills for capability routing when Identity dispatches to an agent
    - Verifying skill existence before dispatch
    - Recording skill usage by Identity policies
    """
    
    def __init__(self, identity_graph: ArcadeDBClient, skills_graph: ArcadeDBClient):
        self.identity = identity_graph
        self.skills = skills_graph
    
    async def verify_skill_for_dispatch(self, delegation_slot_id: str, required_skill: str) -> BridgeResult:
        """Verify a skill exists and is available for an Identity delegation slot
        
        Args:
            delegation_slot_id: The Identity delegation slot
            required_skill: The skill name to verify
            
        Returns:
            BridgeResult with skill verification status
        """
        slot_results = await self.identity.execute(DELEGATION_SLOT_BY_ID, {"slot_id": delegation_slot_id})
        
        if not slot_results:
            return BridgeResult(
                source_graph="identity",
                target_graph="skills",
                source_id=delegation_slot_id,
                metadata={"error": "Delegation slot not found"}
            )
        
        slot = slot_results[0]
        agent_type = slot.get("agent_type", "")
        
        skill_results = await self.skills.execute(SKILL_BY_NAME_PROJECT, {"skill_name": required_skill})
        
        if not skill_results:
            return BridgeResult(
                source_graph="identity",
                target_graph="skills",
                source_id=delegation_slot_id,
                metadata={
                    "skill_found": False,
                    "required_skill": required_skill,
                    "agent_type": agent_type
                }
            )
        
        skill = skill_results[0]
        is_available = skill.get("confidence", 0) > 0.3 and skill.get("decay", 1.0) < 0.7
        
        return BridgeResult(
            source_graph="identity",
            target_graph="skills",
            source_id=delegation_slot_id,
            results=skill_results,
            metadata={
                "skill_found": True,
                "skill_available": is_available,
                "required_skill": required_skill,
                "agent_type": agent_type,
                "confidence": skill.get("confidence", 0),
                "decay": skill.get("decay", 1.0)
            }
        )
    
    async def get_skills_for_policy(self, policy_id: str) -> BridgeResult:
        """Get skills relevant to an Identity policy
        
        Args:
            policy_id: The policy to find skills for
            
        Returns:
            BridgeResult with applicable skills
        """
        policy_results = await self.identity.execute(POLICY_BY_ID, {"policy_id": policy_id})
        
        if not policy_results:
            return BridgeResult(
                source_graph="identity",
                target_graph="skills",
                source_id=policy_id,
                metadata={"error": "Policy not found"}
            )
        
        policy = policy_results[0]
        conditions = policy.get("conditions", "")
        policy_name = policy.get("name", "")
        
        skills = await self.skills.execute(SKILLS_BY_CATEGORY, {"categories": conditions})
        
        return BridgeResult(
            source_graph="identity",
            target_graph="skills",
            source_id=policy_id,
            results=skills,
            metadata={
                "policy_name": policy_name,
                "conditions": conditions,
                "skill_count": len(skills)
            }
        )
    
    async def record_skill_usage(self, skill_id: str, policy_id: str, outcome: str) -> BridgeResult:
        """Record that a skill was used as part of an Identity policy decision
        
        Args:
            skill_id: The skill that was used
            policy_id: The policy that triggered the usage
            outcome: The outcome of the skill execution
            
        Returns:
            BridgeResult with the usage record
        """
        props = {
            "skill_id": skill_id,
            "policy_id": policy_id,
            "outcome": outcome,
            "used_at": datetime.utcnow().isoformat(),
            "source_graph": "identity"
        }
        
        query = "g.addV('skill_usage_record')"
        for key in props:
            query += f".property('{key}', :{key})"
        result = await self.skills.execute(query, props)
        
        return BridgeResult(
            source_graph="identity",
            target_graph="skills",
            source_id=policy_id,
            results=result,
            metadata={
                "skill_id": skill_id,
                "outcome": outcome
            }
        )


class MemorySkillsBridge:
    """Bridge between Memory and Skills graphs
    
    Enables:
    - Storing skill execution results as memory episodes
    - Querying Memory for skill training data
    - Linking skill success/failure to memory facts
    """
    
    def __init__(self, memory_graph: ArcadeDBClient, skills_graph: ArcadeDBClient):
        self.memory = memory_graph
        self.skills = skills_graph
    
    async def store_skill_result_as_episode(self, skill_id: str, result: dict) -> BridgeResult:
        """Store skill execution result as a Memory episode
        
        Args:
            skill_id: The skill that was executed
            result: The execution result data
            
        Returns:
            BridgeResult with the created episode
        """
        skill_results = await self.skills.execute(SKILL_BY_ID, {"skill_id": skill_id})
        
        skill_name = ""
        if skill_results:
            skill_name = skill_results[0].get("name", "")
        
        success = result.get("success", False)
        event_type = "skill_success" if success else "skill_failure"
        
        props = {
            "event_type": event_type,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "participants": ",".join(result.get("participants", ["skill_system"])),
            "timestamp": datetime.utcnow().isoformat(),
            "success": str(success),
            "latency": str(result.get("latency", 0)),
            "output_summary": str(result.get("output_summary", ""))[:500],
        }
        
        query = "g.addV('skill_episode')"
        for key, value in props.items():
            query += f".property('{key}', :{key})"
        episode_result = await self.memory.execute(query, props)
        
        if episode_result and skill_results:
            episode_id = episode_result[0].get("id", "")
            skill_vertex_id = skill_results[0].get("id", "")
            
            edge_bindings = {
                "episode_id": episode_id,
                "skill_id": skill_vertex_id,
                "outcome": event_type,
                "timestamp": datetime.utcnow().isoformat(),
            }
            await self.memory.execute(EXECUTED_SKILL_EDGE, edge_bindings)
        
        return BridgeResult(
            source_graph="skills",
            target_graph="memory",
            source_id=skill_id,
            results=episode_result,
            metadata={
                "skill_name": skill_name,
                "success": success,
                "event_type": event_type
            }
        )
    
    async def get_training_data_for_skill(self, skill_name: str, limit: int = 20) -> BridgeResult:
        """Query Memory for episodes that can be used as training data for a skill
        
        Args:
            skill_name: The skill to find training data for
            limit: Maximum episodes to return
            
        Returns:
            BridgeResult with relevant episodes
        """
        episodes = await self.memory.execute(EPISODE_BY_SKILL_NAME, {"skill_name": skill_name, "limit": limit})
        
        facts = await self.memory.execute(FACTS_BY_PREDICATE_OBJECT, {"skill_name": skill_name, "limit": limit})
        
        return BridgeResult(
            source_graph="skills",
            target_graph="memory",
            source_id=skill_name,
            results={
                "episodes": episodes,
                "facts": facts
            },
            metadata={
                "skill_name": skill_name,
                "episode_count": len(episodes),
                "fact_count": len(facts)
            }
        )
    
    async def update_skill_from_memory_feedback(self, skill_id: str, feedback_type: str,
                                                 confidence_delta: float = 0.0) -> BridgeResult:
        """Update a skill's confidence based on memory feedback
        
        Args:
            skill_id: The skill to update
            feedback_type: Type of feedback (success, failure, contradiction)
            confidence_delta: Amount to adjust confidence
            
        Returns:
            BridgeResult with updated skill info
        """
        success_count = await self.memory.execute(SKILL_EPISODE_COUNT, {"skill_id": skill_id})
        failure_count = await self.memory.execute(SKILL_FAILURE_COUNT, {"skill_id": skill_id})
        
        total = (success_count[0] if success_count else 0) + (failure_count[0] if failure_count else 0)
        success_rate = (success_count[0] / total) if total > 0 else 0.5
        
        if feedback_type == "success":
            confidence_delta = abs(confidence_delta) if confidence_delta != 0 else 0.05
        elif feedback_type == "failure":
            confidence_delta = -abs(confidence_delta) if confidence_delta != 0 else -0.1
        elif feedback_type == "contradiction":
            confidence_delta = -abs(confidence_delta) if confidence_delta != 0 else -0.15
        
        new_confidence = max(0.0, min(1.0, success_rate + confidence_delta))
        
        update_bindings = {
            "skill_id": skill_id,
            "confidence": new_confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }
        result = await self.skills.execute(SKILL_UPDATE_CONFIDENCE, update_bindings)
        
        return BridgeResult(
            source_graph="memory",
            target_graph="skills",
            source_id=skill_id,
            results=result,
            metadata={
                "feedback_type": feedback_type,
                "success_rate": success_rate,
                "confidence_delta": confidence_delta,
                "new_confidence": new_confidence,
                "total_episodes": total
            }
        )


class CrossGraphTraversal:
    """Execute Gremlin traversals across multiple FIHG graphs
    
    Takes a starting graph, query, and target graph to execute
    cross-graph traversals with combined results.
    """
    
    GRAPH_MAP = {
        "identity": "identity",
        "memory": "memory",
        "skills": "skills"
    }
    
    def __init__(self, graph_manager: FIHGGraphManager):
        self.graph_manager = graph_manager
    
    def _get_graph_client(self, graph_name: str) -> ArcadeDBClient:
        """Get the appropriate graph client by name"""
        clients = {
            "identity": self.graph_manager.identity,
            "memory": self.graph_manager.memory,
            "skills": self.graph_manager.skills
        }
        
        client = clients.get(graph_name)
        if not client:
            raise ValueError(f"Unknown graph: {graph_name}. Must be one of {list(clients.keys())}")
        return client
    
    async def traverse(self, source_graph: str, query: str, target_graph: str,
                       bridge_key: str = None, bindings: dict = None) -> BridgeResult:
        """Execute a cross-graph traversal
        
        Args:
            source_graph: Starting graph (identity, memory, skills)
            query: Gremlin query to execute on source graph
            target_graph: Target graph to query with results
            bridge_key: Optional key to use from source results for target query
            bindings: Optional query bindings
            
        Returns:
            BridgeResult with combined results from both graphs
        """
        source_client = self._get_graph_client(source_graph)
        target_client = self._get_graph_client(target_graph)
        
        source_results = await source_client.execute(query, bindings)
        
        if not source_results:
            return BridgeResult(
                source_graph=source_graph,
                target_graph=target_graph,
                source_id="query",
                results={"source": [], "target": []},
                metadata={"source_count": 0, "target_count": 0}
            )
        
        target_results = []
        if bridge_key and source_results:
            bridge_values = []
            for result in source_results:
                if isinstance(result, dict) and bridge_key in result:
                    bridge_values.append(result[bridge_key])
                elif isinstance(result, str):
                    bridge_values.append(result)
            
            if bridge_values:
                values_str = ", ".join([f"'{v}'" for v in bridge_values])
                target_query = f"g.V().hasId(within({values_str}))"
                target_results = await target_client.execute(target_query)
        
        return BridgeResult(
            source_graph=source_graph,
            target_graph=target_graph,
            source_id="query",
            results={
                "source": source_results,
                "target": target_results
            },
            metadata={
                "source_count": len(source_results),
                "target_count": len(target_results),
                "bridge_key": bridge_key
            }
        )
    
    async def traverse_chain(self, traversal_steps: list[dict]) -> BridgeResult:
        """Execute a chain of cross-graph traversals
        
        Args:
            traversal_steps: List of {source_graph, query, target_graph, bridge_key}
            
        Returns:
            BridgeResult with final results
        """
        if not traversal_steps:
            return BridgeResult(
                source_graph="",
                target_graph="",
                source_id="chain",
                results=[],
                metadata={"error": "No traversal steps provided"}
            )
        
        current_results = []
        last_source = ""
        last_target = ""
        
        for i, step in enumerate(traversal_steps):
            source_graph = step["source_graph"]
            query = step["query"]
            target_graph = step.get("target_graph", source_graph)
            bridge_key = step.get("bridge_key")
            
            if i == 0:
                result = await self.traverse(source_graph, query, target_graph, bridge_key)
            else:
                query = step.get("query", f"g.V().hasId(within({self._format_ids(current_results)}))")
                result = await self.traverse(source_graph, query, target_graph, bridge_key)
            
            current_results = result.results.get("target", result.results.get("source", []))
            last_source = source_graph
            last_target = target_graph
        
        return BridgeResult(
            source_graph=traversal_steps[0]["source_graph"],
            target_graph=last_target,
            source_id="chain",
            results=current_results,
            metadata={
                "steps_executed": len(traversal_steps),
                "chain": [f"{s['source_graph']}->{s.get('target_graph', s['source_graph'])}" for s in traversal_steps],
                "result_count": len(current_results)
            }
        )
    
    def _format_ids(self, results: list) -> str:
        """Format result IDs for use in Gremlin query"""
        ids = []
        for result in results:
            if isinstance(result, dict):
                if "id" in result:
                    ids.append(result["id"])
            elif isinstance(result, str):
                ids.append(result)
        return ", ".join([f"'{id}'" for id in ids])


class CrossGraphBridgeManager:
    """Unified manager for all FIHG cross-graph bridges
    
    Provides a single entry point for cross-graph operations
    with automatic bridge selection based on source/target graphs.
    """
    
    def __init__(self, graph_manager: FIHGGraphManager):
        self.graph_manager = graph_manager
        
        self.identity_memory = IdentityMemoryBridge(
            graph_manager.identity, graph_manager.memory
        )
        self.identity_skills = IdentitySkillsBridge(
            graph_manager.identity, graph_manager.skills
        )
        self.memory_skills = MemorySkillsBridge(
            graph_manager.memory, graph_manager.skills
        )
        self.traversal = CrossGraphTraversal(graph_manager)
    
    async def query(self, source_graph: str, target_graph: str,
                    operation: str, **kwargs) -> BridgeResult:
        """Route cross-graph query to appropriate bridge
        
        Args:
            source_graph: Source graph name
            target_graph: Target graph name
            operation: Operation to perform
            **kwargs: Operation-specific arguments
            
        Returns:
            BridgeResult from the appropriate bridge
        """
        bridge_key = f"{source_graph}_{target_graph}"
        
        bridge_map = {
            "identity_memory": self.identity_memory,
            "memory_identity": self.identity_memory,
            "identity_skills": self.identity_skills,
            "skills_identity": self.identity_skills,
            "memory_skills": self.memory_skills,
            "skills_memory": self.memory_skills,
        }
        
        bridge = bridge_map.get(bridge_key)
        if not bridge:
            return BridgeResult(
                source_graph=source_graph,
                target_graph=target_graph,
                source_id="unknown",
                metadata={"error": f"No bridge for {source_graph} -> {target_graph}"}
            )
        
        if hasattr(bridge, operation):
            method = getattr(bridge, operation)
            return await method(**kwargs)
        
        return BridgeResult(
            source_graph=source_graph,
            target_graph=target_graph,
            source_id=operation,
            metadata={"error": f"Operation '{operation}' not found on bridge"}
        )
