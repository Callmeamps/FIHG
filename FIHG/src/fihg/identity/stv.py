"""STV (Single Transferable Vote) implementation for conflict resolution"""

from typing import Optional
from ...db.sqlite_schema import SQLiteSchema


class STVVoting:
    """Single Transferable Vote voting system for FIHG conflict resolution"""
    
    def __init__(self, sqlite_db: SQLiteSchema):
        self.db = sqlite_db
    
    async def rank_candidates(self, candidates: list[dict], criteria: dict = None) -> dict:
        """
        Rank candidates using STV algorithm.
        
        Args:
            candidates: List of {id, scores: {criterion: value}}
            criteria: Optional dict of criteria weights
            
        Returns:
            {winner, runner_ups, rejected, quota, transfers}
        """
        if not candidates:
            return {"winner": None, "runner_ups": [], "rejected": [], "error": "No candidates"}
        
        if len(candidates) == 1:
            return {
                "winner": candidates[0]["id"],
                "runner_ups": [],
                "rejected": []
            }
        
        # Default Identity criteria weights
        if criteria is None:
            criteria = {
                "user_preference_alignment": 0.3,
                "style_consistency": 0.2,
                "policy_compliance": 0.2,
                "brevity_vs_completeness": 0.15,
                "task_complexity_fit": 0.15
            }
        
        # Calculate weighted scores for each candidate
        scored = []
        for candidate in candidates:
            total_score = 0.0
            for criterion, weight in criteria.items():
                score = candidate.get("scores", {}).get(criterion, 0.5)  # default 0.5
                total_score += score * weight
            scored.append({**candidate, "total_score": total_score})
        
        # Sort by total score (descending)
        scored.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Calculate quota (Droop quota)
        vote_count = len(candidates)
        quota = (vote_count / (1 + len(candidates))) + 1  # simplified
        
        # Determine winner (highest score)
        winner = scored[0]["id"]
        runner_ups = [c["id"] for c in scored[1:3]]  # top 2 runner-ups
        rejected = [c["id"] for c in scored[3:]]  # rest are rejected
        
        return {
            "winner": winner,
            "runner_ups": runner_ups,
            "rejected": rejected,
            "quota": quota,
            "scores": {c["id"]: c["total_score"] for c in scored}
        }
    
    async def vote_and_save(self, task_id: str, candidates: list[dict], 
                           criteria: dict = None) -> dict:
        """Run STV and save outcome to database"""
        result = await self.rank_candidates(candidates, criteria)
        
        await self.db.save_stv_outcome(
            task_id=task_id,
            winner=result["winner"],
            runner_ups=result["runner_ups"],
            rejected=result["rejected"]
        )
        
        return result
    
    async def get_runner_ups(self, task_id: str) -> list[str]:
        """Get stored runner-ups for a task"""
        outcome = await self.db.get_stv_outcome(task_id)
        if outcome:
            return outcome["runner_ups"]
        return []
    
    async def promote_runner_up(self, task_id: str) -> Optional[str]:
        """Promote a runner-up if the winner fails"""
        runner_ups = await self.get_runner_ups(task_id)
        if runner_ups:
            return runner_ups[0]  # Return the top runner-up
        return None


class IdentitySTVCriteria:
    """STV criteria presets for Identity FIHG"""
    
    RESPONSE_STYLE = {
        "user_preference_alignment": 0.3,
        "style_consistency": 0.2,
        "policy_compliance": 0.2,
        "brevity_vs_completeness": 0.15,
        "task_complexity_fit": 0.15
    }
    
    AGENT_DISPATCH = {
        "capability_match": 0.35,
        "current_load": 0.2,
        "success_history": 0.25,
        "latency": 0.1,
        "trust": 0.1
    }
    
    POLICY_RESOLUTION = {
        "priority_level": 0.3,
        "specificity": 0.2,
        "recency": 0.15,
        "scope_coverage": 0.2,
        "exception_count": 0.15
    }