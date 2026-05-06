"""Tests for DecayEngine"""

import pytest
from datetime import datetime, timezone, timedelta

from src.core.base import BaseNode, BaseEdge
from src.core.decay import DecayEngine


@pytest.fixture
def engine():
    return DecayEngine(freshness_half_life_hours=24.0)


@pytest.fixture
def fresh_node():
    return BaseNode(
        id="n1", type="test", label="Test Node",
        freshness=1.0, wear=0.0, activity_count=0, error_count=0,
        success_rate=1.0, created_at=datetime.now(timezone.utc),
        last_used_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fresh_edge():
    return BaseEdge(
        id="e1", source="s1", target="t1", relation="test",
        wear=0.0, clarity=1.0, activation_count=0, evidence=[],
        created_at=datetime.now(timezone.utc),
    )


class TestFreshnessDecay:
    def test_no_decay_when_just_used(self, engine, fresh_node):
        new_val = engine.decay_node_freshness(fresh_node)
        assert new_val == pytest.approx(1.0, abs=0.01)

    def test_decay_after_one_half_life(self, engine, fresh_node):
        fresh_node.last_used_at = datetime.now(timezone.utc) - timedelta(hours=24)
        new_val = engine.decay_node_freshness(fresh_node)
        assert new_val == pytest.approx(0.5, abs=0.05)

    def test_decay_after_two_half_lives(self, engine, fresh_node):
        fresh_node.last_used_at = datetime.now(timezone.utc) - timedelta(hours=48)
        new_val = engine.decay_node_freshness(fresh_node)
        assert new_val == pytest.approx(0.25, abs=0.05)

    def test_edge_clarity_decay(self, engine, fresh_edge):
        fresh_edge.created_at = datetime.now(timezone.utc) - timedelta(hours=24)
        new_val = engine.decay_edge_clarity(fresh_edge)
        assert new_val == pytest.approx(0.5, abs=0.05)

    def test_naive_datetime_handled(self, engine, fresh_node):
        fresh_node.last_used_at = datetime.now() - timedelta(hours=24)
        new_val = engine.decay_node_freshness(fresh_node)
        assert 0.0 <= new_val <= 1.0


class TestWearScoring:
    def test_zero_activity_zero_wear(self, engine, fresh_node):
        wear = engine.calculate_node_wear(fresh_node)
        assert wear == 0.0

    def test_high_error_rate_high_wear(self, engine, fresh_node):
        fresh_node.activity_count = 100
        fresh_node.error_count = 80
        wear = engine.calculate_node_wear(fresh_node)
        assert wear > 0.5

    def test_low_error_rate_low_wear(self, engine, fresh_node):
        fresh_node.activity_count = 100
        fresh_node.error_count = 5
        wear = engine.calculate_node_wear(fresh_node)
        assert wear < 0.3

    def test_edge_zero_wear_when_idle(self, engine, fresh_edge):
        wear = engine.calculate_edge_wear(fresh_edge)
        assert wear == 0.0

    def test_edge_wear_with_errors(self, engine, fresh_edge):
        fresh_edge.activation_count = 100
        fresh_edge.evidence = ["err"] * 80
        wear = engine.calculate_edge_wear(fresh_edge)
        assert wear > 0.5

    def test_wear_clamped_to_one(self, engine, fresh_node):
        fresh_node.activity_count = 10000
        fresh_node.error_count = 10000
        wear = engine.calculate_node_wear(fresh_node)
        assert wear <= 1.0


class TestDecayNode:
    def test_returns_metrics(self, engine, fresh_node):
        metrics = engine.decay_node(fresh_node)
        assert "freshness" in metrics
        assert "wear" in metrics
        assert "success_rate" in metrics

    def test_success_rate_degrades_with_wear(self, engine, fresh_node):
        fresh_node.activity_count = 100
        fresh_node.error_count = 50
        fresh_node.success_rate = 0.95
        metrics = engine.decay_node(fresh_node)
        assert metrics["success_rate"] < 0.95

    def test_freshness_at_zero_stays_zero(self, engine, fresh_node):
        fresh_node.freshness = 0.0
        metrics = engine.decay_node(fresh_node)
        assert metrics["freshness"] == 0.0


class TestDecayEdge:
    def test_returns_metrics(self, engine, fresh_edge):
        metrics = engine.decay_edge(fresh_edge)
        assert "clarity" in metrics
        assert "wear" in metrics

    def test_clarity_degrades_with_wear(self, engine, fresh_edge):
        fresh_edge.activation_count = 1000
        fresh_edge.evidence = ["err"] * 500
        metrics = engine.decay_edge(fresh_edge)
        assert metrics["clarity"] <= 1.0


class TestBatchDecay:
    def test_batch_processes_all(self, engine, fresh_node, fresh_edge):
        result = engine.batch_decay([fresh_node], [fresh_edge])
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 1


class TestStaleDetection:
    def test_detects_stale_nodes(self, engine, fresh_node):
        fresh_node.last_used_at = datetime.now(timezone.utc) - timedelta(hours=96)
        stale = engine.get_stale_entities([fresh_node], [], freshness_threshold=0.1)
        assert fresh_node.id in stale["stale_nodes"]

    def test_detects_stale_edges(self, engine, fresh_edge):
        fresh_edge.created_at = datetime.now(timezone.utc) - timedelta(hours=96)
        stale = engine.get_stale_entities([], [fresh_edge], freshness_threshold=0.1)
        assert fresh_edge.id in stale["stale_edges"]

    def test_no_stale_when_fresh(self, engine, fresh_node, fresh_edge):
        stale = engine.get_stale_entities([fresh_node], [fresh_edge], freshness_threshold=0.1)
        assert stale["stale_nodes"] == []
        assert stale["stale_edges"] == []


class TestWornDetection:
    def test_detects_worn_nodes(self, engine, fresh_node):
        fresh_node.activity_count = 1000
        fresh_node.error_count = 900
        worn = engine.get_worn_entities([fresh_node], [], wear_threshold=0.8)
        assert fresh_node.id in worn["worn_nodes"]

    def test_detects_worn_edges(self, engine, fresh_edge):
        fresh_edge.activation_count = 1000
        fresh_edge.evidence = ["err"] * 900
        worn = engine.get_worn_entities([], [fresh_edge], wear_threshold=0.8)
        assert fresh_edge.id in worn["worn_edges"]

    def test_no_worn_when_healthy(self, engine, fresh_node, fresh_edge):
        worn = engine.get_worn_entities([fresh_node], [fresh_edge], wear_threshold=0.8)
        assert worn["worn_nodes"] == []
        assert worn["worn_edges"] == []
