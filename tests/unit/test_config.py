"""Unit tests for configuration schema.

This module tests the Pydantic configuration models including validation,
YAML loading, and default value handling.
"""

import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from alphanso.config.schema import (
    AgentConfig,
    ClaudeAgentConfig,
    ConvergenceConfig,
    OpenAIAgentConfig,
    PreActionConfig,
    RetryStrategyConfig,
)


class TestPreActionConfig:
    """Tests for PreActionConfig model."""

    def test_valid_pre_action_config(self) -> None:
        """Test creating valid PreActionConfig."""
        config = PreActionConfig(
            command="git fetch upstream",
            description="Fetch upstream changes",
        )

        assert config.command == "git fetch upstream"
        assert config.description == "Fetch upstream changes"

    def test_default_description_from_command(self) -> None:
        """Test description defaults to command if not provided."""
        config = PreActionConfig(command="echo test")

        assert config.description == "echo test"

    def test_empty_command_fails_validation(self) -> None:
        """Test that empty command fails validation."""
        with pytest.raises(ValidationError):
            PreActionConfig(command="")


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_default_agent_config(self) -> None:
        """Test AgentConfig with default values."""
        config = AgentConfig()

        assert config.type == "claude-agent-sdk"
        assert config.claude.model == "claude-sonnet-4-5@20250929"
        assert config.openai.model == "gpt-4"

    def test_claude_agent_config(self) -> None:
        """Test AgentConfig with Claude Agent SDK."""
        config = AgentConfig(
            type="claude-agent-sdk",
            claude=ClaudeAgentConfig(
                model="claude-opus-4-5-20250929",
            ),
        )

        assert config.type == "claude-agent-sdk"
        assert config.claude.model == "claude-opus-4-5-20250929"

    def test_openai_agent_config(self) -> None:
        """Test AgentConfig with OpenAI Agent SDK."""
        config = AgentConfig(
            type="openai-agent-sdk",
            openai=OpenAIAgentConfig(
                model="gpt-4-turbo",
            ),
        )

        assert config.type == "openai-agent-sdk"
        assert config.openai.model == "gpt-4-turbo"


class TestRetryStrategyConfig:
    """Tests for RetryStrategyConfig model."""

    def test_default_retry_strategy(self) -> None:
        """Test RetryStrategyConfig defaults."""
        config = RetryStrategyConfig()

        assert config.type == "hybrid"
        assert config.max_tracked_failures == 10

    def test_custom_retry_strategy(self) -> None:
        """Test RetryStrategyConfig with custom values."""
        config = RetryStrategyConfig(
            type="aggressive",
            max_tracked_failures=20,
        )

        assert config.type == "aggressive"
        assert config.max_tracked_failures == 20

    def test_max_tracked_failures_validation(self) -> None:
        """Test max_tracked_failures must be >= 1."""
        with pytest.raises(ValidationError):
            RetryStrategyConfig(max_tracked_failures=0)


class TestConvergenceConfig:
    """Tests for ConvergenceConfig model."""

    def test_minimal_convergence_config(self) -> None:
        """Test creating minimal valid ConvergenceConfig."""
        config = ConvergenceConfig(name="Test Config")

        assert config.name == "Test Config"
        assert config.max_attempts == 10  # default
        assert config.pre_actions == []  # default
        assert isinstance(config.agent, AgentConfig)
        assert isinstance(config.retry_strategy, RetryStrategyConfig)
        assert config.working_directory == "."  # default

    def test_full_convergence_config(self) -> None:
        """Test creating full ConvergenceConfig."""
        config = ConvergenceConfig(
            name="Full Config",
            max_attempts=50,
            pre_actions=[
                PreActionConfig(command="git fetch", description="Fetch"),
                PreActionConfig(command="git merge", description="Merge"),
            ],
            agent=AgentConfig(
                type="claude-agent-sdk",
                claude=ClaudeAgentConfig(model="claude-opus-4-5-20250929"),
            ),
            retry_strategy=RetryStrategyConfig(type="simple"),
            working_directory="/tmp/test",
        )

        assert config.name == "Full Config"
        assert config.max_attempts == 50
        assert len(config.pre_actions) == 2
        assert config.pre_actions[0].command == "git fetch"
        assert config.agent.type == "claude-agent-sdk"
        assert config.agent.claude.model == "claude-opus-4-5-20250929"
        assert config.retry_strategy.type == "simple"
        assert config.working_directory == "/tmp/test"

    def test_empty_name_fails_validation(self) -> None:
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError):
            ConvergenceConfig(name="")

    def test_max_attempts_validation(self) -> None:
        """Test max_attempts validation bounds."""
        # Should accept valid range
        config = ConvergenceConfig(name="Test", max_attempts=100)
        assert config.max_attempts == 100

        # Should reject < 1
        with pytest.raises(ValidationError):
            ConvergenceConfig(name="Test", max_attempts=0)

        # Should reject > 1000
        with pytest.raises(ValidationError):
            ConvergenceConfig(name="Test", max_attempts=1001)

    def test_from_yaml_success(self) -> None:
        """Test loading config from YAML file."""
        yaml_content = """
name: "Test Config"
max_attempts: 20
pre_actions:
  - command: "git fetch upstream"
    description: "Fetch upstream"
  - command: "git merge upstream/main"
    description: "Merge main"
agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"
retry_strategy:
  type: "hybrid"
  max_tracked_failures: 10
working_directory: "/tmp/test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(yaml_path)

            assert config.name == "Test Config"
            assert config.max_attempts == 20
            assert len(config.pre_actions) == 2
            assert config.pre_actions[0].command == "git fetch upstream"
            assert config.agent.type == "claude-agent-sdk"
            assert config.agent.claude.model == "claude-sonnet-4-5-20250929"
            assert config.working_directory == "/tmp/test"
        finally:
            Path(yaml_path).unlink()

    def test_from_yaml_file_not_found(self) -> None:
        """Test loading from non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ConvergenceConfig.from_yaml("/nonexistent/file.yaml")

    def test_from_yaml_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises YAMLError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            yaml_path = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                ConvergenceConfig.from_yaml(yaml_path)
        finally:
            Path(yaml_path).unlink()

    def test_from_yaml_invalid_config(self) -> None:
        """Test loading YAML with invalid config raises ValidationError."""
        yaml_content = """
name: ""
max_attempts: -1
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            with pytest.raises(ValidationError):
                ConvergenceConfig.from_yaml(yaml_path)
        finally:
            Path(yaml_path).unlink()

    def test_to_yaml(self) -> None:
        """Test saving config to YAML file."""
        config = ConvergenceConfig(
            name="Export Test",
            max_attempts=15,
            pre_actions=[
                PreActionConfig(command="echo test", description="Test echo"),
            ],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml_path = f.name

        try:
            config.to_yaml(yaml_path)

            # Load and verify
            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            assert data["name"] == "Export Test"
            assert data["max_attempts"] == 15
            assert len(data["pre_actions"]) == 1
            assert data["pre_actions"][0]["command"] == "echo test"
        finally:
            Path(yaml_path).unlink()

    def test_config_serialization_roundtrip(self) -> None:
        """Test config can be serialized to YAML and loaded back."""
        original = ConvergenceConfig(
            name="Roundtrip Test",
            max_attempts=25,
            pre_actions=[
                PreActionConfig(command="cmd1", description="First"),
                PreActionConfig(command="cmd2", description="Second"),
            ],
            agent=AgentConfig(
                type="claude-agent-sdk",
                claude=ClaudeAgentConfig(model="claude-opus-4-5-20250929"),
            ),
            retry_strategy=RetryStrategyConfig(max_tracked_failures=15),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml_path = f.name

        try:
            original.to_yaml(yaml_path)
            loaded = ConvergenceConfig.from_yaml(yaml_path)

            assert loaded.name == original.name
            assert loaded.max_attempts == original.max_attempts
            assert len(loaded.pre_actions) == len(original.pre_actions)
            assert loaded.agent.type == original.agent.type
            assert loaded.agent.claude.model == original.agent.claude.model
            assert (
                loaded.retry_strategy.max_tracked_failures
                == original.retry_strategy.max_tracked_failures
            )
        finally:
            Path(yaml_path).unlink()
