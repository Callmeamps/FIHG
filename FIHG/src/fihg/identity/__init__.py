"""Identity FIHG - Outward persona, policy, and conflict resolution"""

from .client import IdentityFIHGClient
from .stv import STVVoting

__all__ = ["IdentityFIHGClient", "STVVoting"]


class IdentityFIHG:
    """Identity FIHG main interface"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.stv = STVVoting(db_client)
    
    async def get_response_style(self, task: str) -> dict:
        """Get appropriate response style for task"""
        # Query identity graph for style rules
        pass
    
    async def resolve_conflict(self, candidates: list[dict]) -> dict:
        """Use STV to resolve conflicting candidates"""
        return await self.stv.rank_candidates(candidates)
    
    async def dispatch_to_agent(self, task: str) -> str:
        """Decide which internal agent should handle task"""
        pass