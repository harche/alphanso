"""Claude Agent SDK client wrapper for convergence loop.

This module provides the ConvergenceAgent class which wraps the Claude Agent SDK
to invoke Claude with built-in tools for investigation and fixing.

Supports both Anthropic API and Google Vertex AI.
"""

import asyncio
import logging
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

logger = logging.getLogger(__name__)


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
        """Invoke Claude with validation failure context (synchronous).

        The SDK automatically provides built-in tools (Bash, Read, Write, Edit, etc.)
        for investigation and fixing.

        This is a synchronous wrapper around ainvoke() for backward compatibility
        and use in non-async contexts (e.g., CLI).

        Args:
            system_prompt: System prompt explaining the task and context
            user_message: User message with validation failure details

        Returns:
            Response dict with content, tool_calls, and stop_reason
        """
        # Run async invoke in sync context
        return asyncio.run(self.ainvoke(system_prompt, user_message))

    async def ainvoke(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Invoke Claude with validation failure context (asynchronous).

        The SDK automatically provides built-in tools (Bash, Read, Write, Edit, etc.)
        for investigation and fixing.

        This is the async version for use in async applications (e.g., Kubernetes operators,
        web servers).

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
            # Bypass all permission checks - appropriate for automated convergence loop
            # in controlled environments (user's project directory)
            permission_mode="bypassPermissions",  # Unrestricted mode for automation
        )

        # Combine system prompt and user message
        full_prompt = f"{system_prompt}\n\n{user_message}"

        # Log the context being sent to AI (INFO level - users need to see this)
        logger.info("=" * 70)
        logger.info("CONTEXT SENT TO AI")
        logger.info("=" * 70)
        logger.info("--- SYSTEM PROMPT ---")
        logger.info(system_prompt)
        logger.info("--- USER MESSAGE ---")
        logger.info(user_message)
        logger.info("=" * 70)

        # Collect all response messages
        messages: list[str] = []
        tool_call_count = 0

        logger.info("=" * 70)
        logger.info("CLAUDE'S ACTIONS (STREAMING):")
        logger.info("=" * 70)

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
                            logger.info("💭 Claude says:")
                            logger.info(f"   {text}")

                        # Claude's thinking process
                        elif isinstance(block, ThinkingBlock):
                            logger.info("🤔 Claude is thinking:")
                            logger.info(f"   {block.thinking}")

                        # Tool being used
                        elif isinstance(block, ToolUseBlock):
                            tool_call_count += 1
                            logger.info(f"🔧 Using tool: {block.name}")
                            logger.info(f"   Input: {block.input}")

                        # Tool result
                        elif isinstance(block, ToolResultBlock):
                            logger.info("   ✅ Tool result:")
                            # Tool results can have content
                            if hasattr(block, "content") and block.content is not None:
                                for result_item in block.content:
                                    if isinstance(result_item, TextBlock):
                                        output = result_item.text
                                        # Truncate long output at INFO, full at DEBUG
                                        if len(output) > 1000:
                                            logger.info(f"      {output[:1000]}")
                                            logger.info("      ... (truncated)")
                                            logger.debug(f"   Full tool output: {output}")
                                        else:
                                            logger.info(f"      {output}")

        logger.info("=" * 70)

        return {
            "content": messages,
            "tool_calls": [],  # SDK handles tools internally
            "tool_call_count": tool_call_count,
            "stop_reason": "end_turn",  # Simplified - SDK handles completion
        }
