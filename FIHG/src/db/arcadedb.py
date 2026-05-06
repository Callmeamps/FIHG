"""ArcadeDB client for FIHG graphs"""

from typing import Optional
from gremlin_python.driver.client import Client
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection


class ArcadeDBClient:
    """Client for ArcadeDB graph database using Gremlin"""
    
    def __init__(self, host: str = "localhost", port: int = 8182,
                 graph_name: str = "g"):
        self.host = host
        self.port = port
        self.graph_name = graph_name
        self._connection: Optional[DriverRemoteConnection] = None
        self._client: Optional[Client] = None
    
    async def connect(self):
        """Establish connection to ArcadeDB"""
        self._connection = DriverRemoteConnection(
            f'ws://{self.host}:{self.port}/gremlin',
            self.graph_name
        )
        self._client = Client(self._connection, 'g')
    
    async def disconnect(self):
        """Close connection"""
        if self._client:
            self._client.close()
        if self._connection:
            self._connection.close()
    
    async def execute(self, query: str, bindings: dict = None) -> list:
        """Execute Gremlin query"""
        if not self._client:
            raise RuntimeError("Not connected to ArcadeDB")
        
        result = self._client.submit(query, bindings)
        return list(result)
    
    async def create_vertex(self, label: str, properties: dict) -> dict:
        """Create a vertex with properties"""
        props_str = ", ".join([f"'{k}': '{v}'" for k, v in properties.items()])
        query = f"g.addV('{label}').property({props_str})"
        results = await self.execute(query)
        return results[0] if results else None
    
    async def create_edge(self, source_id: str, target_id: str, 
                          label: str, properties: dict = None) -> dict:
        """Create an edge between two vertices"""
        props_str = ""
        if properties:
            props_str = ".property(" + ", ".join([f"'{k}', '{v}'" for k, v in properties.items()]) + ")"
        
        query = f"g.V('{source_id}').addE('{label}').to(g.V('{target_id}'){props_str})"
        results = await self.execute(query)
        return results[0] if results else None
    
    async def find_vertex(self, label: str, property_key: str, value: str) -> list:
        """Find vertices by label and property"""
        query = f"g.V().has('{label}', '{property_key}', '{value}')"
        return await self.execute(query)
    
    async def traverse(self, start_id: str, *steps: str) -> list:
        """Traverse graph starting from a vertex"""
        steps_str = ".".join(steps)
        query = f"g.V('{start_id}').{steps_str}"
        return await self.execute(query)


class FIHGGraphManager:
    """Manages the three FIHG graphs"""
    
    def __init__(self):
        self.identity: Optional[ArcadeDBClient] = None
        self.memory: Optional[ArcadeDBClient] = None
        self.skills: Optional[ArcadeDBClient] = None
    
    async def connect_all(self, host: str = "localhost", port: int = 8182):
        """Connect to all three FIHG graphs"""
        # In production, each graph might be a separate ArcadeDB instance
        # For development, they can share the same server with different graph names
        self.identity = ArcadeDBClient(host, port, "identity_fihg")
        self.memory = ArcadeDBClient(host, port, "memory_fihg")
        self.skills = ArcadeDBClient(host, port, "skills_fihg")
        
        await self.identity.connect()
        await self.memory.connect()
        await self.skills.connect()
    
    async def disconnect_all(self):
        """Disconnect from all graphs"""
        if self.identity:
            await self.identity.disconnect()
        if self.memory:
            await self.memory.disconnect()
        if self.skills:
            await self.skills.disconnect()