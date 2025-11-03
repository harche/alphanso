"""Unit tests for agent client and prompt builders.

This module tests the ConvergenceAgent class and prompt builder functions
without making real API calls to Claude.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

from alphanso.agent.client import ConvergenceAgent
from alphanso.agent.prompts import build_fix_prompt, build_user_message
from alphanso.graph.state import ConvergenceState


class TestConvergenceAgent:
    """Tests for ConvergenceAgent class."""

    def test_agent_initialization_with_defaults(self) -> None:
        """Test ConvergenceAgent initializes with default parameters."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            assert agent.model == "claude-sonnet-4-5@20250929"
            assert agent.working_directory is not None
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
            {"ANTHROPIC_API_KEY": "", "ANTHROPIC_VERTEX_PROJECT_ID": "test-project"},
            clear=False,
        ):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            assert agent.provider == "vertex"

    def test_agent_initialization_raises_without_provider(self) -> None:
        """Test ConvergenceAgent raises error when no provider is configured."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "",
                "ANTHROPIC_VERTEX_PROJECT_ID": "",
            },
            clear=False,
        ):
            with pytest.raises(ValueError) as exc_info:
                ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            error_msg = str(exc_info.value)
            assert "Neither ANTHROPIC_API_KEY nor ANTHROPIC_VERTEX_PROJECT_ID is set" in error_msg

    def test_agent_invoke_returns_response_dict(self) -> None:
        """Test agent.invoke() returns a properly formatted response dict."""
        # We'll mock the async invoke to avoid actually calling the SDK
        mock_response = {
            "messages": ["test message"],
            "tool_call_count": 3,
            "stop_reason": "end_turn",
        }

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            # Mock the async invoke method
            with patch.object(agent, '_async_invoke', new_callable=AsyncMock, return_value=mock_response):
                response = agent.invoke(
                    system_prompt="You are a test agent",
                    user_message="Fix the build",
                )

                # Verify response structure
                assert "stop_reason" in response
                assert "tool_call_count" in response
                assert response["stop_reason"] == "end_turn"
                assert response["tool_call_count"] == 3

    def test_agent_passes_parameters_to_async_invoke(self) -> None:
        """Test agent passes system_prompt and user_message to async implementation."""
        mock_response = {"messages": [], "tool_call_count": 0, "stop_reason": "end_turn"}

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            with patch.object(agent, '_async_invoke', new_callable=AsyncMock, return_value=mock_response) as mock_async:
                agent.invoke(
                    system_prompt="Test system prompt",
                    user_message="Test user message",
                )

                # Verify async invoke was called with correct parameters
                mock_async.assert_called_once_with("Test system prompt", "Test user message")


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
                        "validator_name": "Build",
                        "success": False,
                        "output": "make: *** [all] Error 2",
                        "stderr": "undefined reference to `foo`",
                        "exit_code": 2,
                        "duration": 1.5,
                        "timestamp": 123456.0,
                        "metadata": {},
                    }
                ]
            ],
        }

        prompt = build_fix_prompt(state)

        # Verify history is included
        assert "Previous attempts:" in prompt
        assert "Attempt 1:" in prompt
        assert "Build: make: *** [all] Error 2" in prompt

    def test_build_fix_prompt_handles_empty_failed_validators(self) -> None:
        """Test build_fix_prompt handles case with no failed validators."""
        state: ConvergenceState = {
            "attempt": 0,
            "max_attempts": 10,
            "failed_validators": [],
            "failure_history": [],
        }

        prompt = build_fix_prompt(state)

        assert "Failed Validators (run by framework, not you):\nNone" in prompt


class TestBuildUserMessage:
    """Tests for build_user_message function."""

    def test_build_user_message_formats_validation_failures(self) -> None:
        """Test build_user_message formats validation failures correctly."""
        state: ConvergenceState = {
            "validation_results": [
                {
                    "validator_name": "Build",
                    "success": False,
                    "output": "Building project...\nmake: *** [all] Error 2",
                    "stderr": "undefined reference to `foo`",
                    "exit_code": 2,
                    "duration": 1.5,
                    "timestamp": 123456.0,
                    "metadata": {},
                }
            ]
        }

        message = build_user_message(state)

        # Verify message structure
        assert "The framework ran validators and the following failed:" in message
        assert "## Validator: Build" in message
        assert "Exit Code: 2" in message
        assert "make: *** [all] Error 2" in message
        assert "undefined reference to `foo`" in message
        assert "Please investigate using SDK tools" in message

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
                    "duration": 0.5,
                    "timestamp": 123456.0,
                    "metadata": {},
                },
                {
                    "validator_name": "Test",
                    "success": False,
                    "output": "FAIL pkg/foo",
                    "stderr": "test_foo failed",
                    "exit_code": 1,
                    "duration": 5.0,
                    "timestamp": 123457.0,
                    "metadata": {},
                },
            ]
        }

        message = build_user_message(state)

        # Should only include Test validator
        assert "Test" in message
        assert "Lint" not in message
        assert "FAIL pkg/foo" in message

    def test_build_user_message_handles_empty_validation_results(self) -> None:
        """Test build_user_message handles empty validation results."""
        state: ConvergenceState = {
            "validation_results": []
        }

        message = build_user_message(state)

        assert "The framework ran validators" in message
        assert "Please investigate using SDK tools" in message
