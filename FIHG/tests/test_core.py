"""Tests for FIHG core module"""

import pytest
from datetime import datetime, timedelta
from src.core.base import BaseNode, BaseEdge, BaseHyperedge, GraphState


class TestBaseNode:
    """Tests for BaseNode"""
    
    def test_create_node(self):
        node = BaseNode(
            id="test_1",
            type="persona",
            label="friendly"
        )
        assert node.id == "test_1"
        assert node.type == "persona"
        assert node.confidence == 0.5
        assert node.state == "active"
    
    def test_node_defaults(self):
        node = BaseNode(id="test_2", type="test", label="test")
        assert node.freshness == 1.0
        assert node.wear == 0.0
        assert node.visibility is True
        assert node.activity_count == 0


class TestBaseEdge:
    """Tests for BaseEdge"""
    
    def test_create_edge(self):
        edge = BaseEdge(
            id="edge_1",
            source="node_1",
            target="node_2",
            relation="depends_on"
        )
        assert edge.id == "edge_1"
        assert edge.source == "node_1"
        assert edge.target == "node_2"
        assert edge.weight == 1.0
    
    def test_edge_with_properties(self):
        edge = BaseEdge(
            id="edge_2",
            source="a",
            target="b",
            relation="transfers_to",
            weight=0.75,
            evidence=["test1", "test2"]
        )
        assert edge.weight == 0.75
        assert len(edge.evidence) == 2


class TestBaseHyperedge:
    """Tests for BaseHyperedge"""
    
    def test_create_hyperedge(self):
        hyperedge = BaseHyperedge(
            id="he_1",
            participants=["node_1", "node_2", "node_3"],
            event_type="conversation",
            role_map={"node_1": "user", "node_2": "synth"}
        )
        assert len(hyperedge.participants) == 3
        assert hyperedge.role_map["node_1"] == "user"


class TestGraphState:
    """Tests for GraphState calculations"""
    
    def test_calculate_brightness_fresh(self):
        """New node with activity should be bright"""
        result = GraphState.calculate_brightness(
            activity_count=50,
            success_rate=0.9,
            last_used=None,
            decay_rate=0.1
        )
        assert result > 0.3
    
    def test_calculate_brightness_stale(self):
        """Old node with no activity should have lower brightness"""
        result = GraphState.calculate_brightness(
            activity_count=0,
            success_rate=1.0,
            last_used=None,
            decay_rate=0.1
        )
        assert result == 0.5  # default
    
    def test_calculate_wear_pristine(self):
        """Never-used node should have no wear"""
        result = GraphState.calculate_wear(0, 0)
        assert result == 0.0
    
    def test_calculate_wear_high_errors(self):
        """Node with high error rate should have high wear"""
        result = GraphState.calculate_wear(100, 50)  # 50% error rate
        assert result > 0.0