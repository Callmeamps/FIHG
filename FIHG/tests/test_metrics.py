"""Tests for metrics aggregation module"""

import pytest
from datetime import timedelta
from src.core.metrics import (
    aggregate_fihg_metrics,
    get_skill_activation_stats,
    get_memory_retrieval_stats,
    get_identity_confidence_stats,
)


class TestAggregateFihgMetrics:
    """Tests for aggregate_fihg_metrics"""

    def test_valid_graph_names(self):
        """Should accept valid graph names"""
        for name in ("identity", "memory", "skills"):
            result = aggregate_fihg_metrics(name)
            assert result["graph_name"] == name

    def test_invalid_graph_name(self):
        """Should raise ValueError for unknown graph"""
        with pytest.raises(ValueError, match="Unknown graph_name"):
            aggregate_fihg_metrics("invalid")

    def test_default_values(self):
        """Should return expected default structure"""
        result = aggregate_fihg_metrics("identity")
        assert result["activity_count"] == 0
        assert result["error_count"] == 0
        assert result["success_rate"] == 1.0
        assert result["average_wear"] == 0.0
        assert result["average_freshness"] == 1.0
        assert result["entity_count"] == 0

    def test_time_window_filter(self):
        """Should include time_window and cutoff when provided"""
        window = timedelta(hours=24)
        result = aggregate_fihg_metrics("memory", time_window=window)
        assert result["time_window"] == window
        assert result["cutoff_time"] is not None

    def test_no_time_window(self):
        """Should have no cutoff when time_window is None"""
        result = aggregate_fihg_metrics("skills", time_window=None)
        assert result["time_window"] is None
        assert result["cutoff_time"] is None

    def test_computed_at_is_present(self):
        """Should include computed_at timestamp"""
        result = aggregate_fihg_metrics("identity")
        assert result["computed_at"] is not None


class TestGetSkillActivationStats:
    """Tests for get_skill_activation_stats"""

    def test_returns_dict(self):
        """Should return a dictionary"""
        result = get_skill_activation_stats()
        assert isinstance(result, dict)

    def test_required_keys(self):
        """Should contain all expected keys"""
        result = get_skill_activation_stats()
        expected_keys = {
            "total_skills",
            "active_skills",
            "inactive_skills",
            "most_activated",
            "least_activated",
            "average_activation_count",
            "average_success_rate",
            "average_latency",
            "skills_needing_refresh",
            "computed_at",
        }
        assert expected_keys.issubset(result.keys())

    def test_default_values(self):
        """Should have sensible defaults"""
        result = get_skill_activation_stats()
        assert result["total_skills"] == 0
        assert result["average_success_rate"] == 1.0
        assert result["skills_needing_refresh"] == []


class TestGetMemoryRetrievalStats:
    """Tests for get_memory_retrieval_stats"""

    def test_returns_dict(self):
        """Should return a dictionary"""
        result = get_memory_retrieval_stats()
        assert isinstance(result, dict)

    def test_required_keys(self):
        """Should contain all expected keys"""
        result = get_memory_retrieval_stats()
        expected_keys = {
            "total_retrievals",
            "hits",
            "misses",
            "hit_rate",
            "average_freshness",
            "average_trust",
            "contradictions_found",
            "most_retrieved",
            "stale_memories",
            "computed_at",
        }
        assert expected_keys.issubset(result.keys())

    def test_default_values(self):
        """Should have sensible defaults"""
        result = get_memory_retrieval_stats()
        assert result["total_retrievals"] == 0
        assert result["hits"] == 0
        assert result["misses"] == 0
        assert result["hit_rate"] == 0.0
        assert result["stale_memories"] == []


class TestGetIdentityConfidenceStats:
    """Tests for get_identity_confidence_stats"""

    def test_returns_dict(self):
        """Should return a dictionary"""
        result = get_identity_confidence_stats()
        assert isinstance(result, dict)

    def test_required_keys(self):
        """Should contain all expected keys"""
        result = get_identity_confidence_stats()
        expected_keys = {
            "overall_confidence",
            "style_consistency",
            "policy_compliance",
            "goal_alignment",
            "identity_entities",
            "high_confidence_count",
            "low_confidence_count",
            "confidence_distribution",
            "computed_at",
        }
        assert expected_keys.issubset(result.keys())

    def test_default_values(self):
        """Should have sensible defaults"""
        result = get_identity_confidence_stats()
        assert result["overall_confidence"] == 0.5
        assert result["style_consistency"] == 1.0
        assert result["policy_compliance"] == 1.0
        assert result["confidence_distribution"] == {}
