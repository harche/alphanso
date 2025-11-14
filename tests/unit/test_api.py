"""Unit tests for API module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError

from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig


class TestRunConvergence:
    """Tests for run_convergence function."""

    def test_run_convergence_with_simple_config(self) -> None:
        """Test run_convergence with a simple working config."""
        config_content = """
name: "Test Config"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "echo 'test output'"
    description: "Test command"

retry_strategy:
  type: "hybrid"
  max_tracked_failures: 10
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Load config and run
            config = ConvergenceConfig.from_yaml(config_path)
            result = run_convergence(config=config)

            # Should succeed
            assert result["success"] is True
            assert result["config_name"] == "Test Config"
            assert len(result["pre_action_results"]) == 1
            assert result["pre_action_results"][0]["success"] is True
            assert "test output" in result["pre_action_results"][0]["output"]
            assert result["working_directory"]
        finally:
            Path(config_path).unlink()

    def test_run_convergence_with_env_vars(self) -> None:
        """Test run_convergence with environment variables."""
        config_content = """
name: "Test Config with Variables"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "echo 'Value: ${TEST_VAR}'"
    description: "Test variable substitution"

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            result = run_convergence(config=config, env_vars={"TEST_VAR": "hello_world"})

            assert result["success"] is True
            assert "hello_world" in result["pre_action_results"][0]["output"]
        finally:
            Path(config_path).unlink()

    def test_run_convergence_adds_current_time_automatically(self) -> None:
        """Test run_convergence adds CURRENT_TIME if not provided."""
        config_content = """
name: "Test Config"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "echo '${CURRENT_TIME}'"
    description: "Test automatic timestamp"

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            result = run_convergence(config=config)

            assert result["success"] is True
            # Should have a timestamp in YYYY-MM-DD HH:MM:SS format
            output = result["pre_action_results"][0]["output"]
            assert "-" in output  # Date separator
            assert ":" in output  # Time separator
        finally:
            Path(config_path).unlink()

    def test_run_convergence_with_failing_action(self) -> None:
        """Test run_convergence with a failing pre-action."""
        config_content = """
name: "Test Config with Failure"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "false"
    description: "This will fail"

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            result = run_convergence(config=config)

            assert result["success"] is False
            assert len(result["pre_action_results"]) == 1
            assert result["pre_action_results"][0]["success"] is False
        finally:
            Path(config_path).unlink()

    def test_run_convergence_with_multiple_actions(self) -> None:
        """Test run_convergence with multiple pre-actions."""
        config_content = """
name: "Test Config with Multiple Actions"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "echo 'first'"
    description: "First action"
  - command: "echo 'second'"
    description: "Second action"
  - command: "echo 'third'"
    description: "Third action"

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            result = run_convergence(config=config)

            assert result["success"] is True
            assert len(result["pre_action_results"]) == 3
            assert "first" in result["pre_action_results"][0]["output"]
            assert "second" in result["pre_action_results"][1]["output"]
            assert "third" in result["pre_action_results"][2]["output"]
        finally:
            Path(config_path).unlink()

    def test_run_convergence_with_nonexistent_file(self) -> None:
        """Test loading config with non-existent file."""
        with pytest.raises(FileNotFoundError):
            ConvergenceConfig.from_yaml("/nonexistent/file.yaml")

    def test_run_convergence_with_invalid_yaml(self) -> None:
        """Test loading config with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                ConvergenceConfig.from_yaml(config_path)
        finally:
            Path(config_path).unlink()

    def test_run_convergence_with_invalid_config_schema(self) -> None:
        """Test loading config with invalid schema."""
        config_content = """
name: ""
max_attempts: -1
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with pytest.raises(ValidationError):
                ConvergenceConfig.from_yaml(config_path)
        finally:
            Path(config_path).unlink()

    def test_run_convergence_partial_failure(self) -> None:
        """Test run_convergence when some actions succeed and some fail."""
        config_content = """
name: "Test Config with Partial Failure"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "echo 'success'"
    description: "This succeeds"
  - command: "false"
    description: "This fails"
  - command: "echo 'also success'"
    description: "This also succeeds"

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            result = run_convergence(config=config)

            # Overall should fail because one action failed
            assert result["success"] is False
            assert len(result["pre_action_results"]) == 3
            assert result["pre_action_results"][0]["success"] is True
            assert result["pre_action_results"][1]["success"] is False
            assert result["pre_action_results"][2]["success"] is True
        finally:
            Path(config_path).unlink()

    def test_run_convergence_returns_correct_working_directory(self) -> None:
        """Test run_convergence returns correct working directory."""
        config_content = """
name: "Test Config"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "echo 'test'"

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            # Pass the working directory explicitly (simulating what CLI does)
            result = run_convergence(
                config=config, working_directory=Path(config_path).parent.absolute()
            )

            # Working directory should be what we passed
            assert result["working_directory"] == str(Path(config_path).parent.absolute())
        finally:
            Path(config_path).unlink()


class TestRecursionLimit:
    """Tests for recursion_limit calculation and passing to graph.invoke()."""

    @patch("alphanso.api.create_convergence_graph")
    def test_recursion_limit_calculated_correctly(self, mock_create_graph) -> None:
        """Test that recursion_limit is calculated as max_attempts * 6 + 10."""
        # Setup mock graph
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "pre_action_results": [],
                "main_script_succeeded": True,
                "working_directory": ".",
            }
        )
        mock_create_graph.return_value = mock_graph

        config_content = """
name: "Test Recursion Limit"
max_attempts: 50

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions: []

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            run_convergence(config=config)

            # Verify graph.ainvoke was called with correct recursion_limit
            assert mock_graph.ainvoke.called
            call_args = mock_graph.ainvoke.call_args

            # Second argument should be the config dict with recursion_limit
            config_dict = call_args[0][1]
            expected_limit = 50 * 6 + 10  # 310
            assert config_dict["recursion_limit"] == expected_limit
        finally:
            Path(config_path).unlink()

    @patch("alphanso.api.create_convergence_graph")
    def test_recursion_limit_with_max_attempts_1(self, mock_create_graph) -> None:
        """Test recursion_limit calculation with max_attempts=1 (edge case)."""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "pre_action_results": [],
                "main_script_succeeded": True,
                "working_directory": ".",
            }
        )
        mock_create_graph.return_value = mock_graph

        config_content = """
name: "Test Recursion Limit Edge Case"
max_attempts: 1

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions: []

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            run_convergence(config=config)

            call_args = mock_graph.ainvoke.call_args
            config_dict = call_args[0][1]
            expected_limit = 1 * 6 + 10  # 16
            assert config_dict["recursion_limit"] == expected_limit
        finally:
            Path(config_path).unlink()

    @patch("alphanso.api.create_convergence_graph")
    def test_recursion_limit_with_max_attempts_100(self, mock_create_graph) -> None:
        """Test recursion_limit calculation with max_attempts=100."""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "pre_action_results": [],
                "main_script_succeeded": True,
                "working_directory": ".",
            }
        )
        mock_create_graph.return_value = mock_graph

        config_content = """
name: "Test Recursion Limit Large"
max_attempts: 100

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions: []

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            run_convergence(config=config)

            call_args = mock_graph.ainvoke.call_args
            config_dict = call_args[0][1]
            expected_limit = 100 * 6 + 10  # 610
            assert config_dict["recursion_limit"] == expected_limit
        finally:
            Path(config_path).unlink()

    @patch("alphanso.api.create_convergence_graph")
    def test_recursion_limit_parameter_passed_to_invoke(self, mock_create_graph) -> None:
        """Test that recursion_limit is actually passed in the config dict to graph.ainvoke()."""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "pre_action_results": [],
                "main_script_succeeded": True,
                "working_directory": ".",
            }
        )
        mock_create_graph.return_value = mock_graph

        config_content = """
name: "Test Recursion Limit Passed"
max_attempts: 25

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions: []

retry_strategy:
  type: "hybrid"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            run_convergence(config=config)

            # Verify invoke was called exactly once
            assert mock_graph.ainvoke.call_count == 1

            # Verify it was called with 2 arguments: state and config
            call_args = mock_graph.ainvoke.call_args
            assert len(call_args[0]) == 2

            # First arg is state dict
            state = call_args[0][0]
            assert isinstance(state, dict)
            assert "max_attempts" in state

            # Second arg is config dict with recursion_limit
            config_dict = call_args[0][1]
            assert isinstance(config_dict, dict)
            assert "recursion_limit" in config_dict
            assert config_dict["recursion_limit"] == 25 * 6 + 10  # 160
        finally:
            Path(config_path).unlink()

    @patch("alphanso.api.create_convergence_graph")
    def test_recursion_limit_with_various_max_attempts(self, mock_create_graph) -> None:
        """Test recursion_limit calculation with various max_attempts values."""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "pre_action_results": [],
                "main_script_succeeded": True,
                "working_directory": ".",
            }
        )
        mock_create_graph.return_value = mock_graph

        test_cases = [
            (1, 16),  # 1 * 6 + 10 = 16
            (5, 40),  # 5 * 6 + 10 = 40
            (10, 70),  # 10 * 6 + 10 = 70
            (50, 310),  # 50 * 6 + 10 = 310
            (100, 610),  # 100 * 6 + 10 = 610
            (200, 1210),  # 200 * 6 + 10 = 1210
        ]

        for max_attempts, expected_limit in test_cases:
            config_content = f"""
name: "Test max_attempts={max_attempts}"
max_attempts: {max_attempts}

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions: []

retry_strategy:
  type: "hybrid"
"""

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(config_content)
                config_path = f.name

            try:
                config = ConvergenceConfig.from_yaml(config_path)
                run_convergence(config=config)

                call_args = mock_graph.ainvoke.call_args
                config_dict = call_args[0][1]
                assert config_dict["recursion_limit"] == expected_limit, (
                    f"For max_attempts={max_attempts}, expected {expected_limit}, "
                    f"got {config_dict['recursion_limit']}"
                )
            finally:
                Path(config_path).unlink()
