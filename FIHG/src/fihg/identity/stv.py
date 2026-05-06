"""STV (Single Transferable Vote) implementation for conflict resolution"""

import json
from typing import Optional, Dict, List
from ...db.sqlite_schema import SQLiteSchema


class STVVoting:
    """Single Transferable Vote voting system for FIHG conflict resolution"""
    
    def __init__(self, sqlite_db: SQLiteSchema):
        self.db = sqlite_db
    
    async def rank_candidates(
        self, 
        candidates: List[Dict], 
        criteria: Dict = None,
        seats: int = 1
    ) -> Dict:
        """
        Rank candidates using enhanced STV algorithm with quota and transfers.
        
        Args:
            candidates: List of {id, scores: {criterion: value}}
            criteria: Optional dict of criteria weights
            seats: Number of winners to elect (default: 1)
            
        Returns:
            {
                winners: list[str],
                runner_ups: list[str],
                rejected: list[str],
                quota: float,
                total_votes: float,
                scores: dict{id: score},
                transfer_values: dict{candidate_id: transfer_value}
            }
        """
        if not candidates:
            return {
                "winners": [], "runner_ups": [], "rejected": [],
                "quota": 0, "total_votes": 0, "scores": {},
                "transfer_values": {},
                "error": "No candidates"
            }
        
        if len(candidates) == 1:
            return {
                "winners": [candidates[0]["id"]],
                "runner_ups": [],
                "rejected": [],
                "quota": 0,
                "total_votes": candidates[0].get("total_score", 1.0),
                "scores": {candidates[0]["id"]: candidates[0].get("total_score", 1.0)},
                "transfer_values": {}
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
        scored_candidates = []
        for candidate in candidates:
            total_score = 0.0
            for criterion, weight in criteria.items():
                score = candidate.get("scores", {}).get(criterion, 0.5)
                total_score += score * weight
            scored_candidates.append({
                "id": candidate["id"],
                "total_score": total_score,
                "original": candidate
            })
        
        # Sort by total score (descending)
        scored_candidates.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Calculate total votes as sum of all scores (simulating vote pool)
        total_votes = sum(c["total_score"] for c in scored_candidates)
        
        # Calculate Droop quota: floor(total_votes / (seats + 1)) + 1
        quota = (total_votes // (seats + 1)) + 1 if seats > 0 else total_votes + 1
        
        # Determine winners (those meeting or exceeding quota)
        winners = []
        runner_ups = []
        rejected = []
        transfer_values = {}
        
        cumulative = 0.0
        for i, candidate in enumerate(scored_candidates):
            if candidate["total_score"] >= quota and len(winners) < seats:
                winners.append(candidate["id"])
                # Calculate surplus transfer value
                surplus = candidate["total_score"] - quota
                transfer_values[candidate["id"]] = surplus
                cumulative += quota  # Track votes used for winners
            elif i < (seats + 2) and len(winners) < seats:
                # If we haven't filled seats, next candidates become interim runner-ups
                runner_ups.append(candidate["id"])
            else:
                rejected.append(candidate["id"])
        
        # If we didn't get enough winners, include top candidates as winners anyway
        if len(winners) < seats:
            needed = seats - len(winners)
            for candidate in scored_candidates:
                if candidate["id"] not in winners and needed > 0:
                    winners.append(candidate["id"])
                    if candidate["id"] not in runner_ups:
                        runner_ups.remove(candidate["id"]) if candidate["id"] in runner_ups else None
                    needed -= 1
        
        # Build scores dict for audit
        scores_dict = {c["id"]: c["total_score"] for c in scored_candidates}
        
        return {
            "winners": winners,
            "runner_ups": runner_ups,
            "rejected": rejected,
            "quota": quota,
            "total_votes": total_votes,
            "scores": scores_dict,
            "transfer_values": transfer_values
        }
    
    async def vote_and_save(
        self, 
        task_id: str, 
        candidates: List[Dict],
        criteria: Dict = None,
        seats: int = 1,
        reason: str = None
    ) -> Dict:
        """Run STV and save outcome to database with full audit data"""
        result = await self.rank_candidates(candidates, criteria, seats)
        
        # Save outcome
        await self.db.save_stv_outcome(
            task_id=task_id,
            winner=result["winners"][0] if result["winners"] else None,
            runner_ups=result["runner_ups"],
            rejected=result["rejected"],
            quota=result["quota"],
            total_votes=result["total_votes"],
            scores=result["scores"],
            transfer_values=result["transfer_values"]
        )
        
        # Archive all runner-ups
        if result["runner_ups"]:
            await self.db.archive_all_runner_ups(task_id, result["runner_ups"], result["scores"])
        
        # Log event
        await self.db.log_event(
            fihg="stv",
            event_type="election_complete",
            payload={
                "task_id": task_id,
                "winner": result["winners"][0] if result["winners"] else None,
                "runner_up_count": len(result["runner_ups"]),
                "quota": result["quota"],
                "reason": reason
            }
        )
        
        return result
    
    async def get_runner_ups(self, task_id: str) -> List[str]:
        """Get stored runner-ups for a task"""
        outcome = await self.db.get_stv_outcome(task_id)
        if outcome:
            return outcome["runner_ups"]
        return []
    
    async def get_full_outcome(self, task_id: str) -> Optional[Dict]:
        """Get complete STV outcome including scores and transfers"""
        return await self.db.get_stv_outcome(task_id)
    
    async def promote_runner_up(
        self, 
        task_id: str, 
        reason: str = "manual_promotion"
    ) -> Optional[str]:
        """
        Promote a runner-up if the winner fails or needs replacement.
        
        Args:
            task_id: Task identifier
            reason: Reason for promotion (e.g., 'winner_failed', 'manual_override')
            
        Returns:
            New winner candidate_id or None
        """
        outcome = await self.db.get_stv_outcome(task_id)
        if not outcome:
            return None
        
        # Check if there are any archived runner-ups
        archived = await self.db.get_archived_runner_ups(task_id, unused_only=True)
        
        if not archived:
            # Fall back to current runner_ups from outcome
            runner_up_ids = outcome["runner_ups"]
            if not runner_up_ids:
                return None
            new_winner_id = runner_up_ids[0]
        else:
            # Pick highest scored unused runner-up
            new_winner_id = archived[0]["candidate_id"]
        
        # Log the promotion
        await self.db.log_promotion(
            task_id=task_id,
            from_winner=outcome["winner"],
            to_runner_up=new_winner_id,
            reason=reason
        )
        
        # Update winner in outcome
        await self.db.update_stv_winner(task_id, new_winner_id, reason)
        
        # Mark archived runner-up as used if applicable
        if archived:
            for a in archived:
                if a["candidate_id"] == new_winner_id:
                    await self.db.mark_archived_runner_up_used(a["id"])
                    break
        
        # Log event
        await self.db.log_event(
            fihg="stv",
            event_type="runner_up_promoted",
            payload={
                "task_id": task_id,
                "previous_winner": outcome["winner"],
                "new_winner": new_winner_id,
                "reason": reason
            }
        )
        
        return new_winner_id
    
    async def archive_runner_ups(self, task_id: str) -> int:
        """
        Archive runner-ups explicitly (though vote_and_save does this automatically).
        
        Returns:
            Number of runner-ups archived
        """
        outcome = await self.db.get_stv_outcome(task_id)
        if not outcome:
            return 0
        
        runner_up_ids = outcome["runner_ups"]
        scores = outcome.get("scores", {})
        
        await self.db.archive_all_runner_ups(task_id, runner_up_ids, scores)
        return len(runner_up_ids)
    
    async def handle_winner_failure(
        self,
        task_id: str,
        failure_reason: str
    ) -> Dict:
        """
        Automatic failure recovery: promote a runner-up when winner fails.
        
        Args:
            task_id: Task identifier
            failure_reason: Why the winner failed
            
        Returns:
            Promotion result dict
        """
        new_winner = await self.promote_runner_up(
            task_id=task_id,
            reason=f"winner_failed: {failure_reason}"
        )
        
        if new_winner:
            return {
                "success": True,
                "new_winner": new_winner,
                "reason": failure_reason
            }
        return {
            "success": False,
            "error": "No runner-ups available for promotion"
        }
    
    async def get_promotion_history(self, task_id: str) -> List[Dict]:
        """Retrieve promotion history for a task"""
        return await self.db.get_promotions(task_id)
    
    async def get_available_archived_runner_ups(self, task_id: str) -> List[Dict]:
        """Get unused archived runner-ups sorted by score"""
        return await self.db.get_archived_runner_ups(task_id, unused_only=True)


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
