"""Unit tests for state schema module.

This module tests the TypedDict definitions and state structure.
"""

from alphanso.graph.state import ConvergenceState, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult TypedDict."""

    def test_validation_result_structure(self) -> None:
        """Test ValidationResult has expected fields."""
        result: ValidationResult = {
            "validator_name": "test_validator",
            "success": True,
            "output": "test output",
            "stderr": "test stderr",
            "exit_code": 0,
            "duration": 1.5,
            "timestamp": 1234567890.0,
            "metadata": {"test": "data"},
        }

        assert result["validator_name"] == "test_validator"
        assert result["success"] is True
        assert result["output"] == "test output"
        assert result["stderr"] == "test stderr"
        assert result["exit_code"] == 0
        assert result["duration"] == 1.5
        assert result["timestamp"] == 1234567890.0
        assert result["metadata"] == {"test": "data"}

    def test_validation_result_with_none_exit_code(self) -> None:
        """Test ValidationResult can have None exit_code."""
        result: ValidationResult = {
            "validator_name": "test",
            "success": False,
            "output": "",
            "stderr": "Exception occurred",
            "exit_code": None,  # Exception case
            "duration": 0.5,
            "timestamp": 1234567890.0,
            "metadata": {},
        }

        assert result["exit_code"] is None
        assert result["success"] is False


class TestConvergenceState:
    """Tests for ConvergenceState TypedDict."""

    def test_convergence_state_with_all_fields(self) -> None:
        """Test ConvergenceState can be created with all fields."""
        state: ConvergenceState = {
            # Pre-actions
            "pre_actions_completed": True,
            "pre_action_results": [],
            "pre_actions_config": [],
            # Loop control
            "attempt": 1,
            "max_attempts": 10,
            "success": False,
            # Validation
            "validation_results": [],
            "failed_validators": [],
            "failure_history": [],
            # AI interaction
            "agent_session_id": None,
            "agent_tool_calls": [],
            "agent_messages": [],
            # Configuration
            "validators_config": [],
            "ai_tools_config": {},
            "retry_strategy": "hybrid",
            # Environment
            "working_directory": "/path/to/dir",
            "env_vars": {},
            # Metadata
            "start_time": 1234567890.0,
            "total_duration": 60.0,
        }

        assert state["pre_actions_completed"] is True
        assert state["attempt"] == 1
        assert state["max_attempts"] == 10
        assert state["success"] is False
        assert state["retry_strategy"] == "hybrid"
        assert state["working_directory"] == "/path/to/dir"

    def test_convergence_state_with_partial_fields(self) -> None:
        """Test ConvergenceState allows partial fields (total=False)."""
        # Should work with only some fields
        state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        assert state["pre_actions_completed"] is False
        assert state["attempt"] == 0

    def test_convergence_state_pre_actions_fields(self) -> None:
        """Test pre-actions related fields."""
        state: ConvergenceState = {
            "pre_actions_completed": True,
            "pre_action_results": [
                {
                    "action": "test",
                    "success": True,
                    "output": "ok",
                    "stderr": "",
                    "exit_code": 0,
                    "duration": 1.0,
                }
            ],
            "pre_actions_config": [{"command": "echo test", "description": "Test"}],
        }

        assert len(state["pre_action_results"]) == 1
        assert state["pre_action_results"][0]["success"] is True
        assert len(state["pre_actions_config"]) == 1

    def test_convergence_state_validation_fields(self) -> None:
        """Test validation related fields."""
        state: ConvergenceState = {
            "validation_results": [
                {
                    "validator_name": "build",
                    "success": False,
                    "output": "build failed",
                    "stderr": "error details",
                    "exit_code": 1,
                    "duration": 30.0,
                    "timestamp": 1234567890.0,
                    "metadata": {"failing_packages": ["pkg1", "pkg2"]},
                }
            ],
            "failed_validators": ["build"],
            "failure_history": [],
        }

        assert len(state["validation_results"]) == 1
        assert state["validation_results"][0]["validator_name"] == "build"
        assert state["failed_validators"] == ["build"]

    def test_convergence_state_ai_fields(self) -> None:
        """Test AI interaction related fields."""
        state: ConvergenceState = {
            "agent_session_id": "session-123",
            "agent_tool_calls": [
                {"tool": "git_diff", "args": {}, "result": "diff output"}
            ],
            "agent_messages": ["Analyzing the failure...", "Fixed the issue"],
        }

        assert state["agent_session_id"] == "session-123"
        assert len(state["agent_tool_calls"]) == 1
        assert len(state["agent_messages"]) == 2

    def test_convergence_state_config_fields(self) -> None:
        """Test configuration related fields."""
        state: ConvergenceState = {
            "validators_config": [
                {"type": "command", "name": "build", "command": "make"}
            ],
            "ai_tools_config": {"enabled": ["git_diff", "read_file"]},
            "retry_strategy": "targeted",
        }

        assert len(state["validators_config"]) == 1
        assert state["retry_strategy"] == "targeted"
        assert "enabled" in state["ai_tools_config"]

    def test_convergence_state_metadata_fields(self) -> None:
        """Test metadata related fields."""
        state: ConvergenceState = {
            "start_time": 1234567890.0,
            "total_duration": 120.5,
            "attempt": 3,
        }

        assert state["start_time"] == 1234567890.0
        assert state["total_duration"] == 120.5
        assert state["attempt"] == 3

    def test_convergence_state_immutability_pattern(self) -> None:
        """Test that state updates follow immutability pattern."""
        # Original state
        state1: ConvergenceState = {
            "attempt": 0,
            "success": False,
        }

        # Create new state with updates (immutable pattern)
        state2 = {**state1, "attempt": 1, "success": True}

        # Original unchanged
        assert state1["attempt"] == 0
        assert state1["success"] is False

        # New state has updates
        assert state2["attempt"] == 1
        assert state2["success"] is True
