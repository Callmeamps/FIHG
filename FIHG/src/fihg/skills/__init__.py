"""Skills FIHG - Capabilities, dependencies, and routing"""

from .client import SkillsFIHGClient
from .routing import SkillRouting

__all__ = ["SkillsFIHGClient", "SkillRouting"]


class SkillsFIHG:
    """Skills FIHG main interface"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.routing = SkillRouting(db_client)
    
    async def get_skill(self, skill_name: str) -> dict:
        """Get skill details including confidence and evidence"""
        pass
    
    async def find_route(self, task: str) -> list[str]:
        """Find the best skill route for a task using STV"""
        return await self.routing.find_best_route(task)
    
    async def update_skill_success(self, skill_id: str, success: bool):
        """Update skill metrics after execution"""
        pass