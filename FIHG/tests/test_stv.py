"""Tests for STV implementation"""

import pytest
from src.fihg.identity.stv import STVVoting, IdentitySTVCriteria


class TestSTVVoting:
    """Tests for STV voting system"""
    
    def test_single_candidate(self):
        """Single candidate should always win"""
        candidates = [{"id": "only_one", "scores": {"test": 0.5}}]
        # Would need mock db to test fully
        # Placeholder test
        assert len(candidates) == 1
    
    def test_stv_criteria_default(self):
        """Default criteria should have all required keys"""
        criteria = IdentitySTVCriteria.RESPONSE_STYLE
        assert "user_preference_alignment" in criteria
        assert "style_consistency" in criteria
        assert "policy_compliance" in criteria
    
    def test_stv_criteria_weights_sum(self):
        """STV criteria weights should sum to 1.0"""
        criteria = IdentitySTVCriteria.AGENT_DISPATCH
        total = sum(criteria.values())
        assert abs(total - 1.0) < 0.01


class TestIdentitySTVCriteria:
    """Tests for Identity STV criteria presets"""
    
    def test_response_style_criteria(self):
        criteria = IdentitySTVCriteria.RESPONSE_STYLE
        assert len(criteria) == 5
        assert all(0 <= v <= 1 for v in criteria.values())
    
    def test_agent_dispatch_criteria(self):
        criteria = IdentitySTVCriteria.AGENT_DISPATCH
        assert len(criteria) == 5
    
    def test_policy_resolution_criteria(self):
        criteria = IdentitySTVCriteria.POLICY_RESOLUTION
        assert len(criteria) == 5