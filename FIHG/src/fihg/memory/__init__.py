"""Memory FIHG - Episodes, facts, and retrieval"""

from .client import MemoryFIHGClient
from .retrieval import MemoryRetrieval

__all__ = ["MemoryFIHGClient", "MemoryRetrieval"]


class MemoryFIHG:
    """Memory FIHG main interface"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.retrieval = MemoryRetrieval(db_client)
    
    async def store_episode(self, episode: dict) -> str:
        """Store a conversation or action episode"""
        pass
    
    async def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        """Retrieve relevant memories for query"""
        return await self.retrieval.search(query, limit)
    
    async def decay_old_memories(self):
        """Apply decay to unused memories"""
        pass