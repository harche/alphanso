"""Tests for main script functionality."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from alphanso.config.schema import MainScriptConfig
from alphanso.graph.edges import check_main_script
from alphanso.graph.nodes import run_main_script_node
from alphanso.graph.state import ConvergenceState, MainScriptResult


class TestMainScriptConfig:
    """Tests for MainScriptConfig pydantic model."""

    def test_valid_main_script_config(self) -> None:
        """Test creating a valid MainScriptConfig."""
        config = MainScriptConfig(
            command="./script.sh --arg=value",
            description="Test script",
            timeout=300.0,
        )

        assert config.command == "./script.sh --arg=value"
        assert config.description == "Test script"
        assert config.timeout == 300.0

    def test_default_description_from_command(self) -> None:
        """Test description defaults to command when not provided."""
        config = MainScriptConfig(command="./my-script.sh")

        assert config.description == "./my-script.sh"

    def test_default_timeout(self) -> None:
        """Test timeout defaults to 600 seconds."""
        config = MainScriptConfig(command="./script.sh")

        assert config.timeout == 600.0

    def test_empty_command_fails_validation(self) -> None:
        """Test that empty command fails validation."""
        with pytest.raises(ValueError):
            MainScriptConfig(command="")

    def test_negative_timeout_fails_validation(self) -> None:
        """Test that negative timeout fails validation."""
        with pytest.raises(ValueError):
            MainScriptConfig(command="test", timeout=-1.0)


class TestRunMainScriptNode:
    """Tests for run_main_script_node function."""

    @patch("subprocess.run")
    def test_successful_script_execution(self, mock_run: MagicMock) -> None:
        """Test successful main script execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Script succeeded",
            stderr="",
        )

        state: ConvergenceState = {
            "main_script_config": {
                "command": "./rebase.sh",
                "description": "Rebase operation",
                "timeout": 600,
            },
            "working_directory": "/test/dir",
            "attempt": 0,
            "max_attempts": 10,
        }

        result = run_main_script_node(state)

        assert result["main_script_succeeded"] is True
        assert result["main_script_result"]["success"] is True
        assert result["main_script_result"]["exit_code"] == 0
        assert "Script succeeded" in result["main_script_result"]["output"]

    @patch("subprocess.run")
    def test_failed_script_execution(self, mock_run: MagicMock) -> None:
        """Test failed main script execution."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: rebase failed",
        )

        state: ConvergenceState = {
            "main_script_config": {
                "command": "./rebase.sh",
                "description": "Rebase operation",
                "timeout": 600,
            },
            "working_directory": "/test/dir",
            "attempt": 0,
            "max_attempts": 10,
        }

        result = run_main_script_node(state)

        assert result["main_script_succeeded"] is False
        assert result["main_script_result"]["success"] is False
        assert result["main_script_result"]["exit_code"] == 1
        assert "rebase failed" in result["main_script_result"]["stderr"]

    @patch("subprocess.run")
    def test_script_timeout(self, mock_run: MagicMock) -> None:
        """Test script timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)

        state: ConvergenceState = {
            "main_script_config": {
                "command": "./long-script.sh",
                "description": "Long running script",
                "timeout": 300,
            },
            "working_directory": "/test/dir",
            "attempt": 0,
            "max_attempts": 10,
        }

        result = run_main_script_node(state)

        assert result["main_script_succeeded"] is False
        assert result["main_script_result"]["success"] is False
        assert result["main_script_result"]["exit_code"] is None
        assert "timed out" in result["main_script_result"]["stderr"]

    @patch("subprocess.run")
    def test_script_exception(self, mock_run: MagicMock) -> None:
        """Test script execution exception handling."""
        mock_run.side_effect = Exception("Command not found")

        state: ConvergenceState = {
            "main_script_config": {
                "command": "./missing-script.sh",
                "description": "Missing script",
                "timeout": 600,
            },
            "working_directory": "/test/dir",
            "attempt": 0,
            "max_attempts": 10,
        }

        result = run_main_script_node(state)

        assert result["main_script_succeeded"] is False
        assert result["main_script_result"]["success"] is False
        assert "Command not found" in result["main_script_result"]["stderr"]

    @patch("subprocess.run")
    def test_respects_timeout_parameter(self, mock_run: MagicMock) -> None:
        """Test that timeout parameter is passed to subprocess."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        state: ConvergenceState = {
            "main_script_config": {
                "command": "./script.sh",
                "description": "Test",
                "timeout": 123.45,
            },
            "working_directory": "/test",
            "attempt": 0,
            "max_attempts": 10,
        }

        run_main_script_node(state)

        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["timeout"] == 123.45

    @patch("subprocess.run")
    def test_respects_working_directory(self, mock_run: MagicMock) -> None:
        """Test that working directory is passed to subprocess."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        state: ConvergenceState = {
            "main_script_config": {
                "command": "./script.sh",
                "description": "Test",
                "timeout": 600,
            },
            "working_directory": "/custom/path",
            "attempt": 0,
            "max_attempts": 10,
        }

        run_main_script_node(state)

        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["cwd"] == "/custom/path"


class TestCheckMainScriptEdge:
    """Tests for check_main_script edge function."""

    def test_script_succeeded_routes_to_end(self) -> None:
        """Test that successful script routes to END."""
        state: ConvergenceState = {
            "main_script_succeeded": True,
        }

        result = check_main_script(state)

        assert result == "end_success"

    def test_script_failed_routes_to_validate(self) -> None:
        """Test that failed script routes to validate."""
        state: ConvergenceState = {
            "main_script_succeeded": False,
        }

        result = check_main_script(state)

        assert result == "continue_to_validate"

    def test_missing_flag_defaults_to_failed(self) -> None:
        """Test that missing succeeded flag defaults to False (validate)."""
        state: ConvergenceState = {}

        result = check_main_script(state)

        assert result == "continue_to_validate"
