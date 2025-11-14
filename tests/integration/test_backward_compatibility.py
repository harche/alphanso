"""Integration tests for backward compatibility.

This module verifies that command-based workflows (YAML configs) continue
to work correctly after adding callable support.
"""

import tempfile
from pathlib import Path

import pytest

from alphanso.config.schema import ConvergenceConfig
from alphanso.graph.nodes import create_validators, pre_actions_node


class TestCommandBasedWorkflow:
    """Tests to ensure command-based workflows still work."""

    def test_load_yaml_config_with_commands(self) -> None:
        """Test loading YAML config with command-based workflow."""
        yaml_content = """
name: "Test Config"
max_attempts: 3
working_directory: "."

pre_actions:
  - command: "echo 'Setup'"
    description: "Setup step"

main_script:
  command: "echo 'Main task'"
  description: "Main task"
  timeout: 30

validators:
  - type: command
    name: "Simple check"
    command: "echo 'Validating'"
    timeout: 10
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)

            # Verify config loaded correctly
            assert config.name == "Test Config"
            assert config.max_attempts == 3
            assert len(config.pre_actions) == 1
            assert config.pre_actions[0].command == "echo 'Setup'"
            assert config.main_script is not None
            assert config.main_script.command == "echo 'Main task'"
            assert len(config.validators) == 1
            assert config.validators[0].command == "echo 'Validating'"

        finally:
            Path(config_path).unlink()

    @pytest.mark.asyncio
    async def test_pre_actions_with_commands(self) -> None:
        """Test pre_actions_node with command-based pre-actions."""
        state = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'Action 1'", "description": "First action"},
                {"command": "echo 'Action 2'", "description": "Second action"},
            ],
            "config_directory": None,
        }

        result = await pre_actions_node(state)

        assert result["pre_actions_completed"] is True
        assert result["pre_actions_failed"] is False
        assert len(result["pre_action_results"]) == 2
        assert result["pre_action_results"][0]["success"] is True
        assert result["pre_action_results"][1]["success"] is True

    def test_create_validators_with_commands(self) -> None:
        """Test create_validators with command-based validators."""
        validators_config = [
            {
                "type": "command",
                "name": "Build",
                "command": "echo 'Building'",
                "timeout": 30,
            },
            {
                "type": "git-conflict",
                "name": "Conflicts",
                "timeout": 10,
            },
        ]

        validators = create_validators(validators_config, working_dir="/tmp")

        assert len(validators) == 2
        assert validators[0].name == "Build"
        assert validators[1].name == "Conflicts"

    def test_yaml_without_callables_validates(self) -> None:
        """Test that YAML configs without callables validate correctly."""
        yaml_content = """
name: "Command Only Config"
max_attempts: 5

pre_actions:
  - command: "ls -la"

validators:
  - type: command
    name: "Check"
    command: "pwd"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config_path = f.name

        try:
            config = ConvergenceConfig.from_yaml(config_path)

            # Should load without errors
            assert config.name == "Command Only Config"
            assert config.pre_actions[0].command == "ls -la"
            assert config.pre_actions[0].callable is None

        finally:
            Path(config_path).unlink()

    def test_config_dict_format_unchanged(self) -> None:
        """Test that config dict format hasn't changed for commands."""
        # This ensures existing code that builds configs programmatically
        # still works without modification
        config_dict = {
            "name": "Test",
            "max_attempts": 3,
            "pre_actions": [{"command": "echo test"}],
            "main_script": {"command": "echo main"},
            "validators": [{"type": "command", "name": "Val", "command": "echo validate"}],
        }

        config = ConvergenceConfig.model_validate(config_dict)

        assert config.pre_actions[0].command == "echo test"
        assert config.main_script.command == "echo main"
        assert config.validators[0].command == "echo validate"
