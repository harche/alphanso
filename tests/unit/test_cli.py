"""Unit tests for CLI module."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from alphanso.cli import cli


class TestCLI:
    """Tests for CLI commands."""

    def test_cli_help(self) -> None:
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Alphanso" in result.output
        assert "AI-assisted iterative problem resolution" in result.output

    def test_cli_version(self) -> None:
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_run_command_help(self) -> None:
        """Test run command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--var" in result.output

    def test_run_command_missing_config(self) -> None:
        """Test run command without config file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_run_command_nonexistent_config(self) -> None:
        """Test run command with non-existent config file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--config", "/nonexistent/file.yaml"])

        assert result.exit_code != 0

    def test_run_command_with_simple_config(self) -> None:
        """Test run command with a simple working config."""
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

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = runner.invoke(cli, ["run", "--config", config_path])

            # Should succeed
            assert result.exit_code == 0
            assert "NODE: pre_actions" in result.output
            assert "Test command" in result.output
            assert "✅" in result.output
            assert "All pre-actions completed successfully" in result.output
        finally:
            Path(config_path).unlink()

    def test_run_command_with_variables(self) -> None:
        """Test run command with environment variables."""
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

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = runner.invoke(
                cli, ["run", "--config", config_path, "--var", "TEST_VAR=hello_world"]
            )

            assert result.exit_code == 0
            assert "hello_world" in result.output
        finally:
            Path(config_path).unlink()

    def test_run_command_with_invalid_variable_format(self) -> None:
        """Test run command with invalid variable format."""
        config_content = """
name: "Test Config"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "echo 'test'"
"""

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = runner.invoke(
                cli, ["run", "--config", config_path, "--var", "INVALID_FORMAT"]
            )

            assert result.exit_code != 0
            assert "Invalid variable format" in result.output
        finally:
            Path(config_path).unlink()

    def test_run_command_with_failing_action(self) -> None:
        """Test run command with a failing pre-action."""
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

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = runner.invoke(cli, ["run", "--config", config_path])

            assert result.exit_code == 1
            assert "❌" in result.output
            assert "Some pre-actions failed" in result.output
        finally:
            Path(config_path).unlink()

    def test_run_command_with_invalid_config(self) -> None:
        """Test run command with invalid YAML config."""
        config_content = """
invalid: yaml: content: [
"""

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = runner.invoke(cli, ["run", "--config", config_path])

            assert result.exit_code == 1
            assert "Error loading configuration" in result.output
        finally:
            Path(config_path).unlink()
