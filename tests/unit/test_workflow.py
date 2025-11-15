"""Tests for workflow configuration and dynamic graph building."""

import pytest

from alphanso.config.schema import EdgeConfig, NodeConfig, WorkflowConfig
from alphanso.graph.builder import build_from_config, validate_topology
from alphanso.graph.conditions import ConditionRegistry
from alphanso.graph.registry import NodeRegistry


class TestNodeRegistry:
    """Tests for NodeRegistry."""

    def test_register_and_get(self):
        """Test registering and retrieving a node."""

        async def test_node(state):
            return {"test": True}

        NodeRegistry.register("test_custom", test_node)
        assert NodeRegistry.is_registered("test_custom")

        retrieved = NodeRegistry.get("test_custom")
        assert retrieved == test_node

    def test_get_nonexistent_raises(self):
        """Test that getting nonexistent node raises ValueError."""
        with pytest.raises(ValueError, match="Unknown node type"):
            NodeRegistry.get("nonexistent_node_12345")

    def test_list_types(self):
        """Test listing all registered node types."""
        types = NodeRegistry.list_types()
        assert isinstance(types, list)
        # Built-in nodes should be present
        assert "pre_actions" in types
        assert "run_main_script" in types
        assert "validate" in types
        assert "ai_fix" in types
        assert "increment_attempt" in types
        assert "decide" in types

    def test_is_registered(self):
        """Test checking if node type is registered."""
        assert NodeRegistry.is_registered("ai_fix")
        assert not NodeRegistry.is_registered("definitely_not_a_node_12345")


class TestConditionRegistry:
    """Tests for ConditionRegistry."""

    def test_register_and_get(self):
        """Test registering and retrieving a condition."""

        def test_condition(state):
            return "test_result"

        ConditionRegistry.register("test_custom_cond", test_condition)
        assert ConditionRegistry.is_registered("test_custom_cond")

        retrieved = ConditionRegistry.get("test_custom_cond")
        assert retrieved == test_condition

    def test_get_nonexistent_raises(self):
        """Test that getting nonexistent condition raises ValueError."""
        with pytest.raises(ValueError, match="Unknown condition"):
            ConditionRegistry.get("nonexistent_condition_12345")

    def test_list_conditions(self):
        """Test listing all registered conditions."""
        conditions = ConditionRegistry.list_conditions()
        assert isinstance(conditions, list)
        # Built-in conditions should be present
        assert "check_pre_actions" in conditions
        assert "check_main_script" in conditions
        assert "should_continue" in conditions

    def test_is_registered(self):
        """Test checking if condition is registered."""
        assert ConditionRegistry.is_registered("should_continue")
        assert not ConditionRegistry.is_registered("definitely_not_a_condition_12345")


class TestWorkflowConfig:
    """Tests for WorkflowConfig schema."""

    def test_minimal_workflow(self):
        """Test creating minimal workflow config."""
        workflow = WorkflowConfig(
            nodes=[NodeConfig(type="pre_actions", name="setup")],
            edges=[
                EdgeConfig(from_node="setup", to_node="END"),
            ],
        )
        assert len(workflow.nodes) == 1
        assert len(workflow.edges) == 1
        assert workflow.entry_point is None  # Should default to first node

    def test_workflow_with_conditional_edges(self):
        """Test workflow with conditional edges."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
                NodeConfig(type="ai_fix", name="fix"),
            ],
            edges=[
                EdgeConfig(
                    from_node="main",
                    to_node=["END", "fix"],
                    condition="check_main_script",
                ),
            ],
        )
        assert len(workflow.nodes) == 3
        # Find the conditional edge
        conditional_edge = next(e for e in workflow.edges if e.condition)
        assert isinstance(conditional_edge.to_node, list)
        assert "END" in conditional_edge.to_node
        assert "fix" in conditional_edge.to_node

    def test_workflow_with_custom_entry_point(self):
        """Test workflow with custom entry point."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="validate", name="check"),
            ],
            edges=[EdgeConfig(from_node="setup", to_node="check")],
            entry_point="setup",
        )
        assert workflow.entry_point == "setup"


class TestTopologyValidation:
    """Tests for topology validation."""

    def test_valid_simple_topology(self):
        """Test that valid simple topology passes validation."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
            ],
            edges=[
                EdgeConfig(from_node="setup", to_node="main"),
                EdgeConfig(from_node="main", to_node="END"),
            ],
        )
        # Should not raise
        validate_topology(workflow)

    def test_unknown_node_type_raises(self):
        """Test that unknown node type raises ValueError."""
        workflow = WorkflowConfig(
            nodes=[NodeConfig(type="unknown_node_type_12345", name="bad")],
            edges=[EdgeConfig(from_node="START", to_node="bad")],
        )
        with pytest.raises(ValueError, match="Unknown node type"):
            validate_topology(workflow)

    def test_duplicate_node_names_raises(self):
        """Test that duplicate node names raise ValueError."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="duplicate"),
                NodeConfig(type="validate", name="duplicate"),
            ],
            edges=[
                EdgeConfig(from_node="duplicate", to_node="END"),
            ],
        )
        with pytest.raises(ValueError, match="Duplicate node names"):
            validate_topology(workflow)

    def test_edge_to_unknown_node_raises(self):
        """Test that edge to unknown node raises ValueError."""
        workflow = WorkflowConfig(
            nodes=[NodeConfig(type="pre_actions", name="setup")],
            edges=[
                EdgeConfig(from_node="setup", to_node="nonexistent"),
            ],
        )
        with pytest.raises(ValueError, match="references unknown node"):
            validate_topology(workflow)

    def test_edge_from_unknown_node_raises(self):
        """Test that edge from unknown node raises ValueError."""
        workflow = WorkflowConfig(
            nodes=[NodeConfig(type="pre_actions", name="setup")],
            edges=[EdgeConfig(from_node="nonexistent", to_node="setup")],
        )
        with pytest.raises(ValueError, match="references unknown node"):
            validate_topology(workflow)

    def test_unknown_condition_raises(self):
        """Test that unknown condition raises ValueError."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
            ],
            edges=[
                EdgeConfig(
                    from_node="setup",
                    to_node=["main", "END"],
                    condition="unknown_condition_12345",
                ),
            ],
        )
        with pytest.raises(ValueError, match="Unknown condition"):
            validate_topology(workflow)

    def test_empty_nodes_raises(self):
        """Test that workflow with no nodes raises ValueError."""
        # Pydantic should enforce min_length=1
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WorkflowConfig(nodes=[], edges=[])

    def test_invalid_entry_point_raises(self):
        """Test that invalid entry point raises ValueError."""
        workflow = WorkflowConfig(
            nodes=[NodeConfig(type="pre_actions", name="setup")],
            edges=[EdgeConfig(from_node="setup", to_node="END")],
            entry_point="nonexistent",
        )
        with pytest.raises(ValueError, match="Entry point"):
            validate_topology(workflow)


class TestGraphBuilding:
    """Tests for dynamic graph building from configuration."""

    def test_build_simple_graph(self):
        """Test building a simple custom graph."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
            ],
            edges=[
                EdgeConfig(from_node="setup", to_node="main"),
                EdgeConfig(
                    from_node="main",
                    to_node=["END", "setup"],
                    condition="check_main_script",
                ),
            ],
            entry_point="setup",
        )

        # Build graph - should not raise
        graph = build_from_config(workflow)
        assert graph is not None

    def test_build_complex_graph(self):
        """Test building a complex custom graph with all node types."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
                NodeConfig(type="ai_fix", name="fix"),
                NodeConfig(type="validate", name="check"),
                NodeConfig(type="decide", name="decide"),
                NodeConfig(type="increment_attempt", name="increment"),
            ],
            edges=[
                EdgeConfig(
                    from_node="setup",
                    to_node=["main", "END"],
                    condition="check_pre_actions",
                ),
                EdgeConfig(
                    from_node="main",
                    to_node=["END", "fix"],
                    condition="check_main_script",
                ),
                EdgeConfig(from_node="fix", to_node="check"),
                EdgeConfig(from_node="check", to_node="decide"),
                EdgeConfig(
                    from_node="decide",
                    to_node=["increment", "END"],
                    condition="should_continue",
                ),
                EdgeConfig(from_node="increment", to_node="main"),
            ],
            entry_point="setup",
        )

        # Build graph - should not raise
        graph = build_from_config(workflow)
        assert graph is not None

    def test_multi_target_edge_without_condition_raises(self):
        """Test that multi-target edge without condition raises ValueError."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main1"),
                NodeConfig(type="run_main_script", name="main2"),
            ],
            edges=[
                # This should raise - multiple targets without condition
                EdgeConfig(from_node="setup", to_node=["main1", "main2"]),
            ],
        )

        # Validation should pass, but building should fail
        validate_topology(workflow)
        with pytest.raises(ValueError, match="multiple targets.*but no condition"):
            build_from_config(workflow)

    def test_build_with_custom_entry_point(self):
        """Test building graph with custom entry point."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
            ],
            edges=[
                EdgeConfig(from_node="setup", to_node="main"),
                EdgeConfig(from_node="main", to_node="END"),
            ],
            entry_point="setup",
        )

        graph = build_from_config(workflow)
        assert graph is not None


class TestBackwardCompatibility:
    """Tests for backward compatibility with default topology."""

    def test_default_topology_has_all_nodes(self):
        """Test that default topology includes all expected nodes."""
        from alphanso.graph.builder import build_default_topology

        graph = build_default_topology()
        assert graph is not None

    def test_create_graph_without_config_uses_default(self):
        """Test that create_convergence_graph() without config uses default."""
        from alphanso.graph.builder import create_convergence_graph

        graph = create_convergence_graph(workflow_config=None)
        assert graph is not None

    def test_create_graph_with_none_uses_default(self):
        """Test that explicitly passing None uses default topology."""
        from alphanso.graph.builder import create_convergence_graph

        graph = create_convergence_graph(None)
        assert graph is not None
