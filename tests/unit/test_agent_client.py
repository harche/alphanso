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
            with patch.object(agent, 'ainvoke', new_callable=AsyncMock, return_value=mock_response):
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

            with patch.object(agent, 'ainvoke', new_callable=AsyncMock, return_value=mock_response) as mock_async:
                agent.invoke(
                    system_prompt="Test system prompt",
                    user_message="Test user message",
                )

                # Verify async invoke was called with correct parameters
                mock_async.assert_called_once_with("Test system prompt", "Test user message")

    @pytest.mark.asyncio
    async def test_ainvoke_streams_messages_from_sdk(self) -> None:
        """Test ainvoke processes streaming messages from Claude SDK."""
        from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock

        # Create mock messages
        mock_message = AssistantMessage(
            content=[
                TextBlock(text="I'll help you fix this issue"),
                ToolUseBlock(id="tool1", name="Bash", input={"command": "ls"}),
            ],
            model="claude-sonnet-4-5@20250929"
        )

        # Mock async iterator
        async def async_iterator():
            yield mock_message

        # Mock the SDK client
        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = MagicMock(return_value=async_iterator())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            with patch("alphanso.agent.client.ClaudeSDKClient", return_value=mock_client):
                response = await agent.ainvoke(
                    system_prompt="You are a test agent",
                    user_message="Fix the issue",
                )

                # Verify response structure
                assert "content" in response
                assert "tool_calls" in response
                assert "tool_call_count" in response
                assert "stop_reason" in response

                # Verify message was collected
                assert "I'll help you fix this issue" in response["content"]
                assert response["tool_call_count"] == 1
                assert response["stop_reason"] == "end_turn"

                # Verify SDK was called correctly
                mock_client.query.assert_called_once()
                call_args = mock_client.query.call_args[0][0]
                assert "You are a test agent" in call_args
                assert "Fix the issue" in call_args

    @pytest.mark.asyncio
    async def test_ainvoke_handles_thinking_blocks(self) -> None:
        """Test ainvoke processes thinking blocks from Claude."""
        from claude_agent_sdk import AssistantMessage, ThinkingBlock, TextBlock

        mock_message = AssistantMessage(
            content=[
                ThinkingBlock(thinking="Let me analyze the error...", signature="test"),
                TextBlock(text="The issue is in the build configuration"),
            ],
            model="claude-sonnet-4-5@20250929"
        )

        async def async_iterator():
            yield mock_message

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = MagicMock(return_value=async_iterator())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            with patch("alphanso.agent.client.ClaudeSDKClient", return_value=mock_client):
                response = await agent.ainvoke(
                    system_prompt="Test",
                    user_message="Test",
                )

                # Thinking blocks are logged but not returned in content
                assert len(response["content"]) == 1
                assert "The issue is in the build configuration" in response["content"]

    @pytest.mark.asyncio
    async def test_ainvoke_handles_tool_results(self) -> None:
        """Test ainvoke processes tool result blocks."""
        from claude_agent_sdk import AssistantMessage, ToolResultBlock, TextBlock

        mock_message = AssistantMessage(
            content=[
                ToolResultBlock(
                    tool_use_id="tool1",
                    content=[TextBlock(text="Command output: file1.txt file2.txt")]
                ),
            ],
            model="claude-sonnet-4-5@20250929"
        )

        async def async_iterator():
            yield mock_message

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = MagicMock(return_value=async_iterator())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(model="claude-sonnet-4-5@20250929")

            with patch("alphanso.agent.client.ClaudeSDKClient", return_value=mock_client):
                response = await agent.ainvoke(
                    system_prompt="Test",
                    user_message="Test",
                )

                # Tool results don't add to content, but are processed
                assert response["tool_call_count"] == 0  # ToolResultBlock doesn't increment
                assert len(response["content"]) == 0

    @pytest.mark.asyncio
    async def test_ainvoke_sets_permission_mode(self) -> None:
        """Test ainvoke sets bypassPermissions mode for automation."""
        from claude_agent_sdk import AssistantMessage, TextBlock

        mock_message = AssistantMessage(
            content=[TextBlock(text="Done")],
            model="claude-sonnet-4-5@20250929"
        )

        async def async_iterator():
            yield mock_message

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = MagicMock(return_value=async_iterator())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agent = ConvergenceAgent(
                model="claude-sonnet-4-5@20250929",
                working_directory="/test/path"
            )

            with patch("alphanso.agent.client.ClaudeSDKClient", return_value=mock_client) as mock_sdk:
                await agent.ainvoke("System", "User")

                # Verify SDK was initialized with correct options
                mock_sdk.assert_called_once()
                options = mock_sdk.call_args[1]["options"]
                assert options.model == "claude-sonnet-4-5@20250929"
                assert options.cwd == "/test/path"
                assert options.permission_mode == "bypassPermissions"


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

        # Verify message structure - validators shown as "failed after your previous fix"
        assert "## Validators Failed After Your Previous Fix" in message
        assert "### Validator: Build" in message
        assert "Exit Code: 2" in message
        assert "make: *** [all] Error 2" in message
        assert "undefined reference to `foo`" in message
        assert "Please refine your approach" in message

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
        """Test build_user_message handles empty validation results (only shows main script error)."""
        state: ConvergenceState = {
            "validation_results": [],
            "main_script_result": {
                "success": False,
                "command": "make rebase",
                "exit_code": 1,
                "stderr": "merge conflict in file.go",
                "output": "",
                "duration": 1.0,
            },
            "main_script_config": {
                "description": "Rebase OpenShift fork",
                "command": "make rebase",
                "timeout": 600,
            },
        }

        message = build_user_message(state)

        # Should show main script error
        assert "## Main Script Failed" in message
        assert "merge conflict in file.go" in message
        assert "Please investigate the main script failure" in message
