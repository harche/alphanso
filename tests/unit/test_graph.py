"""Unit tests for graph builder and execution.

This module tests LangGraph integration and graph execution.
"""

import time

from alphanso.graph.builder import create_convergence_graph
from alphanso.graph.nodes import decide_node, pre_actions_node, validate_node
from alphanso.graph.state import ConvergenceState


class TestGraphNodes:
    """Tests for individual graph nodes."""

    def test_pre_actions_node_returns_partial_updates(self) -> None:
        """Test pre_actions_node returns partial state updates."""
        state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'test'", "description": "Test command"}
            ],
            "env_vars": {},
            "working_directory": ".",
        }

        updates = pre_actions_node(state)

        # Returns partial updates, not full state
        assert "pre_actions_completed" in updates
        assert "pre_action_results" in updates
        assert updates["pre_actions_completed"] is True
        assert len(updates["pre_action_results"]) == 1

    def test_validate_node_placeholder(self) -> None:
        """Test validate_node placeholder returns success."""
        state: ConvergenceState = {"attempt": 0}

        updates = validate_node(state)

        # Placeholder always succeeds
        assert updates["success"] is True
        assert updates["validation_results"] == []
        assert updates["failed_validators"] == []

    def test_decide_node_placeholder(self) -> None:
        """Test decide_node placeholder returns empty dict."""
        state: ConvergenceState = {"success": True}

        updates = decide_node(state)

        # Placeholder returns no updates
        assert updates == {}


class TestGraphBuilder:
    """Tests for graph builder and compilation."""

    def test_create_convergence_graph_compiles(self) -> None:
        """Test graph compiles successfully."""
        graph = create_convergence_graph()

        # Graph should compile without errors
        assert graph is not None

    def test_graph_executes_end_to_end(self) -> None:
        """Test graph executes from START to END."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'hello'", "description": "Test"}
            ],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        final_state = graph.invoke(initial_state)

        # Should reach END with success
        assert final_state["pre_actions_completed"] is True
        assert final_state["success"] is True
        assert len(final_state["pre_action_results"]) == 1

    def test_graph_threads_state_through_nodes(self) -> None:
        """Test state is properly threaded through all nodes."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'step1'", "description": "Step 1"},
                {"command": "echo 'step2'", "description": "Step 2"},
            ],
            "env_vars": {"TEST_VAR": "test_value"},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        final_state = graph.invoke(initial_state)

        # State should preserve original fields
        # Note: pre_actions_node adds WORKING_DIR to env_vars
        assert final_state["env_vars"]["TEST_VAR"] == "test_value"
        assert final_state["attempt"] == 0
        assert final_state["max_attempts"] == 10
        assert final_state["working_directory"] == "."

        # State should have updates from pre_actions_node
        assert final_state["pre_actions_completed"] is True
        assert len(final_state["pre_action_results"]) == 2

        # State should have updates from validate_node
        assert final_state["success"] is True
        assert final_state["validation_results"] == []
        assert final_state["failed_validators"] == []

    def test_graph_execution_performance(self) -> None:
        """Test graph execution completes quickly (< 100ms for simple case)."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [{"command": "echo 'fast'", "description": "Fast"}],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        start = time.time()
        graph.invoke(initial_state)
        duration = time.time() - start

        # Should complete in < 100ms
        assert duration < 0.1

    def test_graph_pre_actions_to_validate_to_decide_flow(self) -> None:
        """Test graph follows pre_actions → validate → decide → END flow."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'flow test'", "description": "Flow test"}
            ],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        final_state = graph.invoke(initial_state)

        # Flow: pre_actions sets completed and results
        assert final_state["pre_actions_completed"] is True
        assert len(final_state["pre_action_results"]) == 1
        assert final_state["pre_action_results"][0]["success"] is True

        # Flow: validate sets success and empty results (placeholder)
        assert final_state["success"] is True
        assert final_state["validation_results"] == []

    def test_graph_handles_multiple_pre_actions(self) -> None:
        """Test graph executes multiple pre-actions sequentially."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'first'", "description": "First"},
                {"command": "echo 'second'", "description": "Second"},
                {"command": "echo 'third'", "description": "Third"},
            ],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        final_state = graph.invoke(initial_state)

        # All pre-actions should be executed
        assert len(final_state["pre_action_results"]) == 3
        assert all(r["success"] for r in final_state["pre_action_results"])

        # Results should be in order
        assert final_state["pre_action_results"][0]["action"] == "First"
        assert final_state["pre_action_results"][1]["action"] == "Second"
        assert final_state["pre_action_results"][2]["action"] == "Third"

    def test_graph_with_failing_pre_action(self) -> None:
        """Test graph continues even when pre-action fails."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'before'", "description": "Before"},
                {"command": "exit 1", "description": "Failing"},
                {"command": "echo 'after'", "description": "After"},
            ],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        final_state = graph.invoke(initial_state)

        # All pre-actions should run (failures don't stop execution)
        assert len(final_state["pre_action_results"]) == 3

        # Middle one failed
        assert final_state["pre_action_results"][0]["success"] is True
        assert final_state["pre_action_results"][1]["success"] is False
        assert final_state["pre_action_results"][2]["success"] is True

        # Validation still succeeds (placeholder)
        assert final_state["success"] is True


class TestGraphStateImmutability:
    """Tests for state immutability patterns."""

    def test_graph_does_not_mutate_initial_state(self) -> None:
        """Test graph doesn't mutate the initial state object."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'test'", "description": "Test"}
            ],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        # Store original values
        original_completed = initial_state["pre_actions_completed"]
        original_success = initial_state["success"]

        # Execute graph
        final_state = graph.invoke(initial_state)

        # Initial state should be unchanged
        assert initial_state["pre_actions_completed"] == original_completed
        assert initial_state["success"] == original_success

        # Final state should have updates
        assert final_state["pre_actions_completed"] is True
        assert final_state["success"] is True
