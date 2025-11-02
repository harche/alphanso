"""Unit tests for agent client and prompt builders.

This module tests the ConvergenceAgent class and prompt builder functions
without making real API calls to Claude.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphanso.agent.client import ConvergenceAgent
from alphanso.agent.prompts import build_fix_prompt, build_user_message
from alphanso.graph.state import ConvergenceState


class TestConvergenceAgent:
    """Tests for ConvergenceAgent class."""

    def test_agent_initialization_with_defaults(self) -> None:
        """Test ConvergenceAgent initializes with default parameters."""
        # Mock environment to have ANTHROPIC_API_KEY set
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            assert agent.model == "claude-sonnet-4-5@20250929"
            assert agent.working_directory is not None
            assert agent.client is not None
            assert agent.provider == "anthropic"

    def test_agent_initialization_with_custom_params(self) -> None:
        """Test ConvergenceAgent initializes with custom parameters."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(
                model="claude-opus-4-20250514",
                working_directory="/custom/path",
            )

            assert agent.model == "claude-opus-4-20250514"
            assert agent.working_directory == "/custom/path"

    def test_agent_initialization_with_vertex_ai(self) -> None:
        """Test ConvergenceAgent initializes with Vertex AI when API key not set."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "", "VERTEX_PROJECT_ID": "test-project"},
            clear=False,
        ):
            # Mock the AnthropicVertex import since it's imported inside __init__
            mock_vertex_instance = MagicMock()
            with patch("anthropic.AnthropicVertex", return_value=mock_vertex_instance):
                agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

                assert agent.provider == "vertex"
                assert agent.client is mock_vertex_instance

    def test_agent_initialization_raises_without_provider(self) -> None:
        """Test ConvergenceAgent raises error when no provider is configured."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "",
                "VERTEX_PROJECT_ID": "",
                "ANTHROPIC_VERTEX_PROJECT_ID": "",
            },
            clear=False,
        ):
            with pytest.raises(ValueError) as exc_info:
                ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            error_msg = str(exc_info.value)
            assert "Neither ANTHROPIC_API_KEY nor VERTEX_PROJECT_ID is set" in error_msg

    def test_agent_invoke_calls_sdk_correctly(self) -> None:
        """Test agent.invoke() calls Anthropic SDK with correct parameters."""
        # Mock response from SDK
        mock_response = MagicMock()
        mock_response.content = []
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=mock_response)

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("alphanso.agent.client.Anthropic", return_value=mock_client):
                agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

                system_prompt = "Test system prompt"
                user_message = "Test user message"

                result = agent.invoke(system_prompt, user_message)

                # Verify SDK was called correctly
                mock_client.messages.create.assert_called_once()
                call_kwargs = mock_client.messages.create.call_args[1]

                assert call_kwargs["model"] == "claude-sonnet-4-5@20250929"
                assert call_kwargs["system"] == system_prompt
                assert call_kwargs["messages"] == [
                    {"role": "user", "content": user_message}
                ]
                assert call_kwargs["tool_choice"] == {"type": "auto"}

                # Verify result structure
                assert "content" in result
                assert "tool_calls" in result
                assert "stop_reason" in result
                assert result["stop_reason"] == "end_turn"

    def test_agent_extracts_tool_calls_from_response(self) -> None:
        """Test agent extracts tool calls from SDK response."""
        # Mock response with tool uses
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "bash"
        mock_tool_block.input = {"command": "git status"}
        mock_tool_block.output = "# On branch main"

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=mock_response)

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("alphanso.agent.client.Anthropic", return_value=mock_client):
                agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

                result = agent.invoke("system", "user")

                # Verify tool calls extracted
                assert len(result["tool_calls"]) == 1
                assert result["tool_calls"][0]["tool"] == "bash"
                assert result["tool_calls"][0]["input"] == {"command": "git status"}
                assert result["tool_calls"][0]["output"] == "# On branch main"


class TestBuildFixPrompt:
    """Tests for build_fix_prompt function."""

    def test_build_fix_prompt_without_custom_prompt(self) -> None:
        """Test build_fix_prompt creates prompt without custom prefix."""
        state: ConvergenceState = {
            "attempt": 0,
            "max_attempts": 10,
            "failed_validators": ["Build", "Test"],
            "failure_history": [],
        }

        prompt = build_fix_prompt(state)

        # Verify basic structure
        assert "Attempt: 1/10" in prompt
        assert "Build, Test" in prompt
        assert "IMPORTANT: The framework runs validators" in prompt
        assert "You have access to investigation and fixing tools" in prompt

    def test_build_fix_prompt_with_custom_prompt(self) -> None:
        """Test build_fix_prompt prepends custom prompt."""
        state: ConvergenceState = {
            "attempt": 2,
            "max_attempts": 5,
            "failed_validators": ["Lint"],
            "failure_history": [],
        }

        custom = "You are a Kubernetes rebasing agent."
        prompt = build_fix_prompt(state, custom_prompt=custom)

        # Verify custom prompt is prepended
        assert prompt.startswith("You are a Kubernetes rebasing agent.")
        assert "---" in prompt  # Separator
        assert "Attempt: 3/5" in prompt
        assert "Lint" in prompt

    def test_build_fix_prompt_includes_failure_history(self) -> None:
        """Test build_fix_prompt includes previous attempt failures."""
        state: ConvergenceState = {
            "attempt": 1,
            "max_attempts": 10,
            "failed_validators": ["Test"],
            "failure_history": [
                [
                    {
                        "validator_name": "Test",
                        "success": False,
                        "output": "FAIL: test_example failed with assertion error",
                        "stderr": "",
                        "exit_code": 1,
                        "duration": 1.5,
                        "timestamp": 123456.0,
                        "metadata": {},
                    }
                ]
            ],
        }

        prompt = build_fix_prompt(state)

        # Verify failure history included
        assert "Previous attempts:" in prompt
        assert "Attempt 1:" in prompt
        assert "Test: FAIL: test_example failed" in prompt

    def test_build_fix_prompt_handles_empty_failed_validators(self) -> None:
        """Test build_fix_prompt handles no failed validators gracefully."""
        state: ConvergenceState = {
            "attempt": 0,
            "max_attempts": 10,
            "failed_validators": [],
            "failure_history": [],
        }

        prompt = build_fix_prompt(state)

        # Should not crash and should include "None"
        assert "Failed Validators" in prompt
        assert "None" in prompt or prompt.count("Failed Validators") > 0


class TestBuildUserMessage:
    """Tests for build_user_message function."""

    def test_build_user_message_formats_validation_failures(self) -> None:
        """Test build_user_message formats validation results correctly."""
        state: ConvergenceState = {
            "validation_results": [
                {
                    "validator_name": "Build",
                    "success": False,
                    "output": "make: *** [all] Error 2",
                    "stderr": "undefined reference to `foo`",
                    "exit_code": 2,
                    "duration": 5.0,
                    "timestamp": 123456.0,
                    "metadata": {},
                }
            ]
        }

        message = build_user_message(state)

        # Verify formatting
        assert "## Validator: Build" in message
        assert "Exit Code: 2" in message
        assert "make: *** [all] Error 2" in message
        assert "undefined reference to `foo`" in message
        assert "Please investigate using SDK tools" in message

    def test_build_user_message_includes_metadata(self) -> None:
        """Test build_user_message includes validator metadata."""
        state: ConvergenceState = {
            "validation_results": [
                {
                    "validator_name": "Test",
                    "success": False,
                    "output": "5 tests failed",
                    "stderr": "",
                    "exit_code": 1,
                    "duration": 10.0,
                    "timestamp": 123456.0,
                    "metadata": {
                        "failing_packages": ["pkg/foo", "pkg/bar"]
                    },
                }
            ]
        }

        message = build_user_message(state)

        # Verify metadata included
        assert "Metadata:" in message
        assert "failing_packages" in message

    def test_build_user_message_skips_successful_validators(self) -> None:
        """Test build_user_message only includes failed validators."""
        state: ConvergenceState = {
            "validation_results": [
                {
                    "validator_name": "Lint",
                    "success": True,
                    "output": "All checks passed",
                    "stderr": "",
                    "exit_code": 0,
                    "duration": 1.0,
                    "timestamp": 123456.0,
                    "metadata": {},
                },
                {
                    "validator_name": "Test",
                    "success": False,
                    "output": "FAIL",
                    "stderr": "",
                    "exit_code": 1,
                    "duration": 2.0,
                    "timestamp": 123457.0,
                    "metadata": {},
                },
            ]
        }

        message = build_user_message(state)

        # Only failed validator should be included
        assert "Test" in message
        assert "Lint" not in message
        assert "All checks passed" not in message

    def test_build_user_message_handles_empty_validation_results(self) -> None:
        """Test build_user_message handles no validation results gracefully."""
        state: ConvergenceState = {"validation_results": []}

        message = build_user_message(state)

        # Should not crash
        assert "The framework ran validators" in message
        assert "Please investigate" in message
