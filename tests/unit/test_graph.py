"""Unit tests for graph builder and execution.

This module tests LangGraph integration and graph execution.
"""

import pytest
import time
from typing import Any
from unittest.mock import patch

from alphanso.graph.builder import create_convergence_graph
from alphanso.graph.nodes import decide_node, pre_actions_node, validate_node
from alphanso.graph.state import ConvergenceState


async def mock_ai_fix_node(state: ConvergenceState) -> dict[str, Any]:
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


def create_test_state(**overrides: Any) -> ConvergenceState:
    """Create a test ConvergenceState with all required fields.

    This helper ensures all tests include the new main_script_config field.
    """
    base_state: ConvergenceState = {
        "pre_actions_completed": False,
        "pre_actions_config": [],
        "env_vars": {},
        "attempt": 0,
        "max_attempts": 10,
        "success": False,
        "working_directory": ".",
        "validators_config": [],  # No validators = success
        "main_script_config": {
            "command": "echo 'test script'",
            "description": "Test main script",
            "timeout": 600,
        },
    }
    base_state.update(overrides)
    return base_state


class TestGraphNodes:
    """Tests for individual graph nodes."""

    @pytest.mark.asyncio
    async def test_pre_actions_node_returns_partial_updates(self) -> None:
        """Test pre_actions_node returns partial state updates."""
        state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'test'", "description": "Test command"}
            ],
            "env_vars": {},
            "working_directory": ".",
        }

        updates = await pre_actions_node(state)

        # Returns partial updates, not full state
        assert "pre_actions_completed" in updates
        assert "pre_action_results" in updates
        assert updates["pre_actions_completed"] is True
        assert len(updates["pre_action_results"]) == 1

    @pytest.mark.asyncio
    async def test_validate_node_placeholder(self) -> None:
        """Test validate_node placeholder returns success."""
        state: ConvergenceState = {"attempt": 0}

        updates = await validate_node(state)

        # Placeholder always succeeds
        assert updates["success"] is True
        assert updates["validation_results"] == []
        assert updates["failed_validators"] == []

    @pytest.mark.asyncio
    async def test_decide_node_placeholder(self) -> None:
        """Test decide_node placeholder returns empty dict."""
        state: ConvergenceState = {"success": True}

        updates = await decide_node(state)

        # Placeholder returns no updates
        assert updates == {}


class TestGraphBuilder:
    """Tests for graph builder and compilation."""

    def test_create_convergence_graph_compiles(self) -> None:
        """Test graph compiles successfully."""
        graph = create_convergence_graph()

        # Graph should compile without errors
        assert graph is not None

    @patch("alphanso.graph.nodes.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_graph_executes_end_to_end(self) -> None:
        """Test graph executes from START to END with main script success."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[{"command": "echo 'hello'", "description": "Test"}],
        )

        final_state = await graph.ainvoke(initial_state)

        # Should reach END with script success
        assert final_state["pre_actions_completed"] is True
        assert final_state["main_script_succeeded"] is True
        assert len(final_state["pre_action_results"]) == 1

    @pytest.mark.asyncio
    async def test_graph_threads_state_through_nodes(self) -> None:
        """Test state is properly threaded through all nodes."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[
                {"command": "echo 'step1'", "description": "Step 1"},
                {"command": "echo 'step2'", "description": "Step 2"},
            ],
            env_vars={"TEST_VAR": "test_value"},
        )

        final_state = await graph.ainvoke(initial_state)

        # State should preserve original fields
        # Note: pre_actions_node adds WORKING_DIR to env_vars
        assert final_state["env_vars"]["TEST_VAR"] == "test_value"
        assert final_state["attempt"] == 0
        assert final_state["max_attempts"] == 10
        assert final_state["working_directory"] == "."

        # State should have updates from pre_actions_node
        assert final_state["pre_actions_completed"] is True
        assert len(final_state["pre_action_results"]) == 2

        # State should have updates from main script
        # Main script succeeded, so workflow ends without running validation
        assert final_state["main_script_succeeded"] is True
        # Validation never runs when main script succeeds, so success/validation fields not set
        assert final_state.get("success") is None or final_state.get("success") is False
        assert final_state.get("validation_results") is None
        assert final_state.get("failed_validators") is None

    @pytest.mark.asyncio
    async def test_graph_execution_performance(self) -> None:
        """Test graph execution completes quickly (< 100ms for simple case)."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[{"command": "echo 'fast'", "description": "Fast"}],
        )

        start = time.time()
        await graph.ainvoke(initial_state)
        duration = time.time() - start

        # Should complete in < 100ms
        assert duration < 0.1

    @pytest.mark.asyncio
    async def test_graph_pre_actions_to_validate_to_decide_flow(self) -> None:
        """Test graph follows pre_actions → run_main_script → END (success) flow."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[
                {"command": "echo 'flow test'", "description": "Flow test"}
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # Flow: pre_actions sets completed and results
        assert final_state["pre_actions_completed"] is True
        assert len(final_state["pre_action_results"]) == 1
        assert final_state["pre_action_results"][0]["success"] is True

        # Flow: main script succeeds, so we skip validation and go to END
        assert final_state["main_script_succeeded"] is True
        # Validation never runs when main script succeeds
        assert final_state.get("validation_results") is None

    @pytest.mark.asyncio
    async def test_graph_handles_multiple_pre_actions(self) -> None:
        """Test graph executes multiple pre-actions sequentially."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[
                {"command": "echo 'first'", "description": "First"},
                {"command": "echo 'second'", "description": "Second"},
                {"command": "echo 'third'", "description": "Third"},
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # All pre-actions should be executed
        assert len(final_state["pre_action_results"]) == 3
        assert all(r["success"] for r in final_state["pre_action_results"])

        # Results should be in order
        assert final_state["pre_action_results"][0]["action"] == "First"
        assert final_state["pre_action_results"][1]["action"] == "Second"
        assert final_state["pre_action_results"][2]["action"] == "Third"

    @pytest.mark.asyncio
    async def test_graph_with_failing_pre_action(self) -> None:
        """Test graph ends immediately when pre-action fails."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[
                {"command": "echo 'before'", "description": "Before"},
                {"command": "exit 1", "description": "Failing"},
                {"command": "echo 'after'", "description": "After"},
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # All pre-actions should run (failures don't stop execution within pre_actions_node)
        assert len(final_state["pre_action_results"]) == 3

        # Middle one failed
        assert final_state["pre_action_results"][0]["success"] is True
        assert final_state["pre_action_results"][1]["success"] is False
        assert final_state["pre_action_results"][2]["success"] is True

        # When any pre-action fails, workflow terminates immediately
        assert final_state["pre_actions_failed"] is True
        # Main script never runs
        assert final_state.get("main_script_succeeded") is None


class TestGraphStateImmutability:
    """Tests for state immutability patterns."""

    @pytest.mark.asyncio
    async def test_graph_does_not_mutate_initial_state(self) -> None:
        """Test graph doesn't mutate the initial state object."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[
                {"command": "echo 'test'", "description": "Test"}
            ],
        )

        # Store original values
        original_completed = initial_state["pre_actions_completed"]
        original_success = initial_state["success"]

        # Execute graph
        final_state = await graph.ainvoke(initial_state)

        # Initial state should be unchanged
        assert initial_state["pre_actions_completed"] == original_completed
        assert initial_state["success"] == original_success

        # Final state should have updates
        assert final_state["pre_actions_completed"] is True
        # With new script-centric workflow, main script succeeds so we skip validation
        assert final_state["main_script_succeeded"] is True


class TestGraphRetryLoop:
    """Tests for STEP 3: Retry loop with conditional edges."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt_goes_to_end(self) -> None:
        """Test that successful main script on first attempt goes directly to END."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[],
            validators_config=[],  # No validators = success
        )

        final_state = await graph.ainvoke(initial_state)

        # Main script succeeds on first attempt
        assert final_state["main_script_succeeded"] is True
        assert final_state["attempt"] == 0  # Never incremented
        # Validation never runs when main script succeeds
        assert final_state.get("failure_history") is None

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_failure_with_attempts_remaining_increments(self) -> None:
        """Test that validation failure with attempts remaining increments attempt."""
        graph = create_convergence_graph()

        # Make main script fail so that validation runs
        # Validators also fail to trigger retry loop
        initial_state = create_test_state(
            pre_actions_config=[],
            max_attempts=3,
            main_script_config={
                "command": "false",  # Main script always fails
                "description": "Failing main script",
                "timeout": 10,
            },
            validators_config=[
                {
                    "type": "command",
                    "name": "Always Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # Should fail after max attempts
        assert final_state["success"] is False
        assert final_state["attempt"] == 2  # 0-indexed, so 2 = 3rd attempt
        assert len(final_state["failure_history"]) == 3  # All 3 attempts
        assert len(final_state["failed_validators"]) > 0

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_max_attempts_reached_goes_to_end_failure(self) -> None:
        """Test that max attempts reached goes to END with failure."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[],
            max_attempts=2,  # Only 2 attempts
            main_script_config={
                "command": "false",  # Main script always fails
                "description": "Failing main script",
                "timeout": 10,
            },
            validators_config=[
                {
                    "type": "command",
                    "name": "Always Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # Should stop after 2 attempts
        assert final_state["success"] is False
        assert final_state["attempt"] == 1  # 0-indexed (attempt 0, 1 = 2 attempts)
        assert len(final_state["failure_history"]) == 2

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_failure_history_tracked_correctly(self) -> None:
        """Test that failure history accumulates correctly across attempts."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[],
            max_attempts=3,
            main_script_config={
                "command": "false",  # Main script always fails
                "description": "Failing main script",
                "timeout": 10,
            },
            validators_config=[
                {
                    "type": "command",
                    "name": "Failing Test",
                    "command": "false",
                    "timeout": 10,
                }
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # Failure history should have all attempts
        assert len(final_state["failure_history"]) == 3

        # Each history entry should be a list of ValidationResults
        for history_entry in final_state["failure_history"]:
            assert isinstance(history_entry, list)
            assert len(history_entry) > 0  # Has validation results
            assert history_entry[0]["validator_name"] == "Failing Test"
            assert history_entry[0]["success"] is False

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_attempt_counter_increments_correctly(self) -> None:
        """Test that attempt counter increments on each retry."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[],
            max_attempts=5,
            main_script_config={
                "command": "false",  # Main script always fails
                "description": "Failing main script",
                "timeout": 10,
            },
            validators_config=[
                {
                    "type": "command",
                    "name": "Fail",
                    "command": "exit 1",
                    "timeout": 10,
                }
            ],
        )

        # Calculate recursion limit: max_attempts * 6 + 10
        final_state = await graph.ainvoke(initial_state, {"recursion_limit": 5 * 6 + 10})

        # After 5 attempts (0-4), should be at attempt 4
        assert final_state["attempt"] == 4
        assert len(final_state["failure_history"]) == 5

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_graph_executes_multiple_retry_loops(self) -> None:
        """Test that graph can execute multiple validation loops."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[],
            max_attempts=4,
            main_script_config={
                "command": "false",  # Main script always fails
                "description": "Failing main script",
                "timeout": 10,
            },
            validators_config=[
                {
                    "type": "command",
                    "name": "Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # Should have looped 4 times
        # Attempt progression: 0 → 1 → 2 → 3
        assert final_state["attempt"] == 3
        assert len(final_state["failure_history"]) == 4

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_state_preserved_across_iterations(self) -> None:
        """Test that state fields are preserved across retry loop iterations."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[],
            env_vars={"CUSTOM_VAR": "preserved_value"},
            max_attempts=3,
            working_directory="/custom/path",
            main_script_config={
                "command": "false",  # Main script always fails
                "description": "Failing main script",
                "timeout": 10,
            },
            validators_config=[
                {
                    "type": "command",
                    "name": "Fail",
                    "command": "false",
                    "timeout": 10,
                }
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # Original state fields should be preserved
        assert final_state["env_vars"]["CUSTOM_VAR"] == "preserved_value"
        assert final_state["working_directory"] == "/custom/path"
        assert final_state["max_attempts"] == 3

    def test_should_continue_edge_function_routing(self) -> None:
        """Test that should_continue() returns correct routing decisions."""
        from alphanso.graph.edges import should_continue

        # Test validators passed case - should retry main script (not end)
        state_validators_passed: ConvergenceState = {
            "success": True,
            "attempt": 0,
            "max_attempts": 10,
        }
        assert should_continue(state_validators_passed) == "validators_passed"

        # Test max attempts reached
        state_max: ConvergenceState = {
            "success": False,
            "attempt": 9,
            "max_attempts": 10,
        }
        assert should_continue(state_max) == "end_failure"

        # Test retry case (validators failed)
        state_retry: ConvergenceState = {
            "success": False,
            "attempt": 2,
            "max_attempts": 10,
        }
        assert should_continue(state_retry) == "retry"

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_integration_with_failing_validator(self) -> None:
        """Integration test with real failing validator demonstrating retry loop."""
        graph = create_convergence_graph()

        initial_state = create_test_state(
            pre_actions_config=[
                {"command": "echo 'Setup complete'", "description": "Setup"}
            ],
            max_attempts=3,
            main_script_config={
                "command": "false",  # Main script always fails
                "description": "Failing main script",
                "timeout": 10,
            },
            validators_config=[
                {
                    "type": "command",
                    "name": "File Check",
                    "command": "test -f /nonexistent/file.txt",  # Will always fail
                    "timeout": 10,
                }
            ],
        )

        final_state = await graph.ainvoke(initial_state)

        # Pre-actions should complete
        assert final_state["pre_actions_completed"] is True
        assert len(final_state["pre_action_results"]) == 1

        # Should fail after retries
        assert final_state["success"] is False
        assert final_state["attempt"] == 2  # 3 attempts (0, 1, 2)
        assert len(final_state["failure_history"]) == 3
        assert "File Check" in final_state["failed_validators"]

    @pytest.mark.asyncio
    async def test_validators_pass_retries_main_script_without_ai_fix(self) -> None:
        """Test that when validators pass, main script is retried without AI fix."""
        graph = create_convergence_graph()

        # Track how many times the main script runs
        # First attempt: fails
        # Second attempt (after validators pass): should succeed
        attempt_counter = {"count": 0}

        def main_script_that_succeeds_on_retry(state: ConvergenceState) -> dict:
            """Main script that fails first time, succeeds on retry."""
            attempt_counter["count"] += 1
            if attempt_counter["count"] == 1:
                # First attempt fails
                return {
                    "main_script_result": {
                        "command": "test script",
                        "success": False,
                        "output": "Failed first time",
                        "stderr": "Error",
                        "exit_code": 1,
                        "duration": 0.1,
                    },
                    "main_script_succeeded": False,
                }
            else:
                # Second attempt succeeds
                return {
                    "main_script_result": {
                        "command": "test script",
                        "success": True,
                        "output": "Success on retry",
                        "stderr": "",
                        "exit_code": 0,
                        "duration": 0.1,
                    },
                    "main_script_succeeded": True,
                }

        # Patch both run_main_script_node and ai_fix_node
        with patch("alphanso.graph.builder.run_main_script_node", main_script_that_succeeds_on_retry):
            with patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node):
                graph = create_convergence_graph()

                initial_state = create_test_state(
                    pre_actions_config=[
                        {"command": "echo 'Setup'", "description": "Setup"}
                    ],
                    max_attempts=10,
                    main_script_config={
                        "command": "test script",
                        "description": "Test script",
                        "timeout": 10,
                    },
                    validators_config=[
                        {
                            "type": "command",
                            "name": "Build",
                            "command": "echo 'Build passed'",  # Always passes
                            "timeout": 10,
                        }
                    ],
                )

                final_state = await graph.ainvoke(initial_state)

                # Main script should have run exactly 2 times
                assert attempt_counter["count"] == 2

                # First attempt: main script failed, validators passed
                # Second attempt: main script succeeded
                assert final_state["main_script_succeeded"] is True

                # Should have incremented attempt once (from 0 to 1)
                assert final_state["attempt"] == 1

                # Validators passed, so no failed validators
                assert len(final_state.get("failed_validators", [])) == 0

    @patch("alphanso.graph.builder.ai_fix_node", mock_ai_fix_node)
    @pytest.mark.asyncio
    async def test_validators_fail_goes_to_ai_fix_not_main_script(self) -> None:
        """Test that when validators fail, we go to AI fix (not retry main script)."""
        graph = create_convergence_graph()

        # Track which nodes get called
        call_sequence = []

        async def tracking_ai_fix_node(state: ConvergenceState) -> dict:
            """Track when AI fix is called."""
            call_sequence.append("ai_fix")
            return await mock_ai_fix_node(state)

        async def tracking_main_script_node(state: ConvergenceState) -> dict:
            """Track when main script is called."""
            call_sequence.append("main_script")
            # Always fail so validators run
            return {
                "main_script_result": {
                    "command": "test script",
                    "success": False,
                    "output": "Main script failed",
                    "stderr": "Error",
                    "exit_code": 1,
                    "duration": 0.1,
                },
                "main_script_succeeded": False,
            }

        with patch("alphanso.graph.builder.ai_fix_node", tracking_ai_fix_node):
            with patch("alphanso.graph.builder.run_main_script_node", tracking_main_script_node):
                graph = create_convergence_graph()

                initial_state = create_test_state(
                    pre_actions_config=[],
                    max_attempts=3,
                    main_script_config={
                        "command": "test script",
                        "description": "Test script",
                        "timeout": 10,
                    },
                    validators_config=[
                        {
                            "type": "command",
                            "name": "Build",
                            "command": "false",  # Always fails
                            "timeout": 10,
                        }
                    ],
                )

                final_state = await graph.ainvoke(initial_state)

                # Verify the call sequence shows AI fix is called after validator failures
                # Expected sequence:
                # 1. main_script (fails)
                # 2. ai_fix (first attempt to fix)
                # 3. validators run and fail
                # 4. ai_fix (second attempt to fix - refinement)
                # 5. validators run and fail
                # 6. ai_fix (third attempt to fix - refinement)
                # 7. max attempts reached → END

                # Should have 3 AI fix calls (one per attempt)
                ai_fix_count = call_sequence.count("ai_fix")
                assert ai_fix_count == 3, f"Expected 3 AI fix calls, got {ai_fix_count}. Sequence: {call_sequence}"

                # Should have exactly 1 main script call (initial failure that triggers the loop)
                main_script_count = call_sequence.count("main_script")
                assert main_script_count == 1, f"Expected 1 main script call, got {main_script_count}. Sequence: {call_sequence}"

                # Verify first call is main_script, then all subsequent calls are ai_fix
                assert call_sequence[0] == "main_script"
                assert all(call == "ai_fix" for call in call_sequence[1:]), f"After main_script fails, should only call ai_fix. Sequence: {call_sequence}"

                # Should end with failure after max attempts
                assert final_state["success"] is False
                assert final_state["attempt"] == 2  # 3 attempts (0, 1, 2)
