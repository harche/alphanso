"""Unit tests for graph builder and execution.

This module tests LangGraph integration and graph execution.
"""

import time
from typing import Any
from unittest.mock import patch

from alphanso.graph.builder import create_convergence_graph
from alphanso.graph.nodes import decide_node, pre_actions_node, validate_node
from alphanso.graph.state import ConvergenceState


def mock_ai_fix_node(state: ConvergenceState) -> dict[str, Any]:
    """Mock ai_fix_node that returns empty dict without calling real agent.

    This prevents tests from requiring ANTHROPIC_API_KEY or making real API calls.
    """
    return {
        "ai_response": {
            "content": ["Mock AI response"],
            "tool_calls": [],
            "tool_call_count": 0,
            "stop_reason": "end_turn",
        }
    }


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


class TestGraphRetryLoop:
    """Tests for STEP 3: Retry loop with conditional edges."""

    def test_success_on_first_attempt_goes_to_end(self) -> None:
        """Test that successful validation on first attempt goes directly to END."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
            "validators_config": [],  # No validators = success
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Should succeed on first attempt
        assert final_state["success"] is True
        assert final_state["attempt"] == 0  # Never incremented
        assert len(final_state["failure_history"]) == 0

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    def test_failure_with_attempts_remaining_increments(self) -> None:
        """Test that validation failure with attempts remaining increments attempt."""
        from alphanso.validators.command import CommandValidator

        graph = create_convergence_graph()

        # Create a failing validator (command that always fails)
        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 3,
            "success": False,
            "working_directory": ".",
            "validators_config": [
                {
                    "type": "command",
                    "name": "Always Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Should fail after max attempts
        assert final_state["success"] is False
        assert final_state["attempt"] == 2  # 0-indexed, so 2 = 3rd attempt
        assert len(final_state["failure_history"]) == 3  # All 3 attempts
        assert len(final_state["failed_validators"]) > 0

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    def test_max_attempts_reached_goes_to_end_failure(self) -> None:
        """Test that max attempts reached goes to END with failure."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 2,  # Only 2 attempts
            "success": False,
            "working_directory": ".",
            "validators_config": [
                {
                    "type": "command",
                    "name": "Always Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Should stop after 2 attempts
        assert final_state["success"] is False
        assert final_state["attempt"] == 1  # 0-indexed (attempt 0, 1 = 2 attempts)
        assert len(final_state["failure_history"]) == 2

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    def test_failure_history_tracked_correctly(self) -> None:
        """Test that failure history accumulates correctly across attempts."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 3,
            "success": False,
            "working_directory": ".",
            "validators_config": [
                {
                    "type": "command",
                    "name": "Failing Test",
                    "command": "false",
                    "timeout": 10,
                }
            ],
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Failure history should have all attempts
        assert len(final_state["failure_history"]) == 3

        # Each history entry should be a list of ValidationResults
        for history_entry in final_state["failure_history"]:
            assert isinstance(history_entry, list)
            assert len(history_entry) > 0  # Has validation results
            assert history_entry[0]["validator_name"] == "Failing Test"
            assert history_entry[0]["success"] is False

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    def test_attempt_counter_increments_correctly(self) -> None:
        """Test that attempt counter increments on each retry."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 5,
            "success": False,
            "working_directory": ".",
            "validators_config": [
                {
                    "type": "command",
                    "name": "Fail",
                    "command": "exit 1",
                    "timeout": 10,
                }
            ],
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # After 5 attempts (0-4), should be at attempt 4
        assert final_state["attempt"] == 4
        assert len(final_state["failure_history"]) == 5

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    def test_graph_executes_multiple_retry_loops(self) -> None:
        """Test that graph can execute multiple validation loops."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 4,
            "success": False,
            "working_directory": ".",
            "validators_config": [
                {
                    "type": "command",
                    "name": "Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Should have looped 4 times
        # Attempt progression: 0 → 1 → 2 → 3
        assert final_state["attempt"] == 3
        assert len(final_state["failure_history"]) == 4

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    def test_state_preserved_across_iterations(self) -> None:
        """Test that state fields are preserved across retry loop iterations."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {"CUSTOM_VAR": "preserved_value"},
            "attempt": 0,
            "max_attempts": 3,
            "success": False,
            "working_directory": "/custom/path",
            "validators_config": [
                {
                    "type": "command",
                    "name": "Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Original state fields should be preserved
        assert final_state["env_vars"]["CUSTOM_VAR"] == "preserved_value"
        assert final_state["working_directory"] == "/custom/path"
        assert final_state["max_attempts"] == 3

    def test_should_continue_edge_function_routing(self) -> None:
        """Test that should_continue() returns correct routing decisions."""
        from alphanso.graph.edges import should_continue

        # Test success case
        state_success: ConvergenceState = {
            "success": True,
            "attempt": 0,
            "max_attempts": 10,
        }
        assert should_continue(state_success) == "end_success"

        # Test max attempts reached
        state_max: ConvergenceState = {
            "success": False,
            "attempt": 9,
            "max_attempts": 10,
        }
        assert should_continue(state_max) == "end_failure"

        # Test retry case
        state_retry: ConvergenceState = {
            "success": False,
            "attempt": 2,
            "max_attempts": 10,
        }
        assert should_continue(state_retry) == "retry"

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    def test_integration_with_failing_validator(self) -> None:
        """Integration test with real failing validator demonstrating retry loop."""
        graph = create_convergence_graph()

        initial_state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'Setup complete'", "description": "Setup"}
            ],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 3,
            "success": False,
            "working_directory": ".",
            "validators_config": [
                {
                    "type": "command",
                    "name": "File Check",
                    "command": "test -f /nonexistent/file.txt",  # Will always fail
                    "timeout": 10,
                }
            ],
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Pre-actions should complete
        assert final_state["pre_actions_completed"] is True
        assert len(final_state["pre_action_results"]) == 1

        # Should fail after retries
        assert final_state["success"] is False
        assert final_state["attempt"] == 2  # 3 attempts (0, 1, 2)
        assert len(final_state["failure_history"]) == 3
        assert "File Check" in final_state["failed_validators"]
