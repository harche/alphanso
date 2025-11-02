"""Unit tests for API module."""

import tempfile
from pathlib import Path

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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            result = run_convergence(
                config=config, env_vars={"TEST_VAR": "hello_world"}
            )

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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)
            # Pass the working directory explicitly (simulating what CLI does)
            result = run_convergence(
                config=config,
                working_directory=Path(config_path).parent.absolute()
            )

            # Working directory should be what we passed
            assert result["working_directory"] == str(Path(config_path).parent.absolute())
        finally:
            Path(config_path).unlink()
