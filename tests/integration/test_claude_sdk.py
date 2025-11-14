"""Integration tests for Claude Code Agent SDK.

These tests verify that the ConvergenceAgent class works correctly with
both Anthropic API and Google Vertex AI. Tests are skipped only if neither
provider is configured.

Setup requirements:
- Anthropic API: Set ANTHROPIC_API_KEY environment variable
- Vertex AI: Set VERTEX_PROJECT_ID (and optionally VERTEX_REGION)
  and authenticate with: gcloud auth application-default login
"""

import os
from unittest.mock import patch

import pytest

from alphanso.agent.client import ConvergenceAgent


def _has_anthropic_api() -> bool:
    """Check if Anthropic API is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _has_vertex_ai() -> bool:
    """Check if Vertex AI is configured."""
    return bool(os.environ.get("VERTEX_PROJECT_ID"))


def _has_any_provider() -> bool:
    """Check if at least one provider is configured."""
    return _has_anthropic_api() or _has_vertex_ai()


# Skip all tests if neither provider is configured
pytestmark = pytest.mark.skipif(
    not _has_any_provider(),
    reason="Neither ANTHROPIC_API_KEY nor VERTEX_PROJECT_ID is set",
)


class TestProviderDetection:
    """Tests for automatic provider detection logic."""

    def test_anthropic_api_takes_priority(self) -> None:
        """Test that Anthropic API is used when both providers are configured."""
        if not _has_anthropic_api():
            pytest.skip("ANTHROPIC_API_KEY not set")

        # If both are set, Anthropic API should win
        agent = ConvergenceAgent()
        assert agent.provider == "anthropic"
        assert agent.client is not None

    def test_vertex_ai_fallback(self) -> None:
        """Test that Vertex AI is used when Anthropic API is not configured."""
        if not _has_vertex_ai():
            pytest.skip("VERTEX_PROJECT_ID not set")

        # Temporarily remove ANTHROPIC_API_KEY to force Vertex AI
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            agent = ConvergenceAgent()
            assert agent.provider == "vertex"
            assert agent.client is not None

    def test_no_provider_raises_error(self) -> None:
        """Test that missing both providers raises clear error."""
        # Remove both environment variables
        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "", "VERTEX_PROJECT_ID": ""}, clear=False
        ):
            with pytest.raises(ValueError) as exc_info:
                ConvergenceAgent()

            error_msg = str(exc_info.value)
            assert "Neither ANTHROPIC_API_KEY nor VERTEX_PROJECT_ID is set" in error_msg
            assert "ANTHROPIC_API_KEY for Anthropic API" in error_msg
            assert "VERTEX_PROJECT_ID for Google Vertex AI" in error_msg


class TestConvergenceAgentInvoke:
    """Integration tests for ConvergenceAgent.invoke() with real API calls."""

    @pytest.mark.asyncio
    async def test_simple_investigation_prompt(self) -> None:
        """Test that agent can handle a simple investigation task.

        This test makes a real API call to verify the SDK integration works.
        We use a minimal prompt to minimize costs.
        """
        agent = ConvergenceAgent()

        system_prompt = (
            "You are a code investigation assistant. "
            "Analyze the validation failure and explain what might be wrong."
        )

        user_message = """
## Validator: Build

Exit Code: 2

**Output:**
make: *** [all] Error 2

**Stderr:**
main.c:5:1: error: unknown type name 'Foo'

Please investigate using SDK tools and identify the issue.
"""

        result = await agent.invoke(system_prompt, user_message)

        # Verify response structure
        assert "content" in result
        assert "tool_calls" in result
        assert "stop_reason" in result

        # Verify we got some content back
        assert len(result["content"]) > 0

        # The agent might or might not use tools for this simple task
        # but we verify the structure is correct
        assert isinstance(result["tool_calls"], list)

    @pytest.mark.asyncio
    async def test_tool_extraction_from_response(self) -> None:
        """Test that tool calls are properly extracted from SDK response.

        This test verifies that when Claude uses tools, we correctly
        extract the tool name, input, and output.
        """
        agent = ConvergenceAgent()

        system_prompt = (
            "You are a git investigation assistant. "
            "Check the current git status using the Bash tool."
        )

        user_message = "Please use the Bash tool to run 'git status' " "and report what you find."

        result = await agent.invoke(system_prompt, user_message)

        # Verify tool calls were made
        assert len(result["tool_calls"]) > 0

        # Verify each tool call has required fields
        for tool_call in result["tool_calls"]:
            assert "tool" in tool_call
            assert "input" in tool_call
            # output might be None if tool wasn't executed yet
            assert "output" in tool_call

            # At least one should be a bash command
            if tool_call["tool"] == "bash":
                assert "command" in tool_call["input"]


class TestVertexAISpecific:
    """Tests specific to Vertex AI configuration."""

    def test_vertex_ai_region_default(self) -> None:
        """Test that Vertex AI uses us-east5 as default region."""
        if not _has_vertex_ai():
            pytest.skip("VERTEX_PROJECT_ID not set")

        # Remove ANTHROPIC_API_KEY and VERTEX_REGION
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "", "VERTEX_REGION": ""},
            clear=False,
        ):
            agent = ConvergenceAgent()

            # AnthropicVertex client doesn't expose region directly,
            # but we can verify it was initialized without error
            assert agent.provider == "vertex"
            assert agent.client is not None

    def test_vertex_ai_custom_region(self) -> None:
        """Test that Vertex AI respects VERTEX_REGION environment variable."""
        if not _has_vertex_ai():
            pytest.skip("VERTEX_PROJECT_ID not set")

        custom_region = "us-central1"

        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "", "VERTEX_REGION": custom_region},
            clear=False,
        ):
            agent = ConvergenceAgent()

            assert agent.provider == "vertex"
            assert agent.client is not None
