"""Claude Agent SDK client wrapper for convergence loop.

This module provides the ConvergenceAgent class which wraps the Claude Agent SDK
to invoke Claude with built-in tools for investigation and fixing.

Supports both Anthropic API and Google Vertex AI.
"""

import asyncio
import os
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)


class ConvergenceAgent:
    """Wrapper around Claude Agent SDK for convergence loop.

    This class provides a simple interface to invoke Claude with the SDK's
    built-in tools (Bash, Read, Write, Edit, Grep, etc.) for investigation and fixing.

    The SDK automatically provides all necessary tools - no custom tool
    creation is needed.

    Supports both Anthropic API and Google Vertex AI:
    - Anthropic API: Set ANTHROPIC_API_KEY environment variable
    - Vertex AI: Set ANTHROPIC_VERTEX_PROJECT_ID and authenticate with
      `gcloud auth application-default login`
    """

    def __init__(
        self,
        model: str,
        working_directory: str | None = None,
    ):
        """Initialize Claude Agent SDK client.

        Args:
            model: Claude model to use (e.g., "claude-sonnet-4-5@20250929")
            working_directory: Working directory for commands (optional)
        """
        self.model = model
        self.working_directory = working_directory or os.getcwd()

        # Determine provider based on environment variables
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
        elif os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID"):
            self.provider = "vertex"
        else:
            raise ValueError(
                "Neither ANTHROPIC_API_KEY nor ANTHROPIC_VERTEX_PROJECT_ID is set. "
                "Please configure one of:\n"
                "  - ANTHROPIC_API_KEY for Anthropic API\n"
                "  - ANTHROPIC_VERTEX_PROJECT_ID for Google Vertex AI "
                "(also run: gcloud auth application-default login)"
            )

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Invoke Claude with validation failure context.

        The SDK automatically provides built-in tools (Bash, Read, Write, Edit, etc.)
        for investigation and fixing.

        Args:
            system_prompt: System prompt explaining the task and context
            user_message: User message with validation failure details

        Returns:
            Response dict with content, tool_calls, and stop_reason
        """
        # Run async invoke in sync context
        return asyncio.run(self._async_invoke(system_prompt, user_message))

    async def _async_invoke(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Async implementation of invoke.

        Args:
            system_prompt: System prompt explaining the task
            user_message: User message with details

        Returns:
            Response dict with collected messages and tool usage
        """
        # Configure Claude Agent SDK options
        options = ClaudeAgentOptions(
            model=self.model,
            cwd=self.working_directory,
            # Let SDK automatically select appropriate tools
            permission_mode="acceptEdits",  # Auto-accept file edits
        )

        # Combine system prompt and user message
        full_prompt = f"{system_prompt}\n\n{user_message}"

        # Collect all response messages
        messages: list[str] = []
        tool_call_count = 0

        print("=" * 70)
        print("CLAUDE'S ACTIONS (STREAMING):")
        print("=" * 70)
        print()

        # Use Claude Agent SDK with streaming
        async with ClaudeSDKClient(options=options) as client:
            # Send query
            await client.query(full_prompt)

            # Stream responses in real-time
            async for message in client.receive_response():
                # Only process AssistantMessage types
                if isinstance(message, AssistantMessage):
                    # Process each content block
                    for block in message.content:
                        # Text responses from Claude
                        if isinstance(block, TextBlock):
                            text = block.text
                            messages.append(text)
                            print(f"💭 Claude says:")
                            print(f"   {text}")
                            print()

                        # Claude's thinking process
                        elif isinstance(block, ThinkingBlock):
                            print(f"🤔 Claude is thinking:")
                            print(f"   {block.thinking}")
                            print()

                        # Tool being used
                        elif isinstance(block, ToolUseBlock):
                            tool_call_count += 1
                            print(f"🔧 Using tool: {block.name}")
                            print(f"   Input: {block.input}")
                            print()

                        # Tool result
                        elif isinstance(block, ToolResultBlock):
                            print(f"   ✅ Tool result:")
                            # Tool results can have content
                            if hasattr(block, "content"):
                                for result_item in block.content:
                                    if isinstance(result_item, TextBlock):
                                        output = result_item.text
                                        # Truncate long output
                                        if len(output) > 1000:
                                            print(f"      {output[:1000]}")
                                            print(f"      ... (truncated)")
                                        else:
                                            print(f"      {output}")
                            print()

        print("=" * 70)
        print()

        return {
            "content": messages,
            "tool_calls": [],  # SDK handles tools internally
            "tool_call_count": tool_call_count,
            "stop_reason": "end_turn",  # Simplified - SDK handles completion
        }
