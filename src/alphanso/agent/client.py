"""Claude Code Agent SDK client wrapper for convergence loop.

This module provides the ConvergenceAgent class which wraps the Anthropic SDK
to invoke Claude with built-in tools for investigation and fixing.

Supports both Anthropic API and Google Vertex AI.
"""

import os
from typing import Any, Union, cast

from anthropic import Anthropic
from anthropic.types import MessageParam


class ConvergenceAgent:
    """Wrapper around Claude Code Agent SDK for convergence loop.

    This class provides a simple interface to invoke Claude with the SDK's
    built-in tools (Bash, Read, Edit, Grep, Glob) for investigation and fixing.

    The SDK automatically provides all necessary tools - no custom tool
    creation is needed.

    Supports both Anthropic API and Google Vertex AI:
    - Anthropic API: Set ANTHROPIC_API_KEY environment variable
    - Vertex AI: Authenticate with `gcloud auth application-default login`
      and optionally set VERTEX_PROJECT_ID and VERTEX_REGION environment variables
    """

    def __init__(
        self,
        model: str,
        working_directory: str | None = None,
    ):
        """Initialize Claude Agent SDK client.

        Automatically detects whether to use Anthropic API or Vertex AI based on:
        1. If ANTHROPIC_API_KEY is set → use Anthropic API
        2. Otherwise → try Vertex AI (requires gcloud authentication)

        Args:
            model: Claude model to use (required - specify the model available in your environment)
            working_directory: Working directory for commands (optional)

        Raises:
            ImportError: If Vertex AI dependencies are not installed
            ValueError: If neither Anthropic API nor Vertex AI is configured
        """
        self.model = model
        self.working_directory = working_directory or os.getcwd()

        # Try Anthropic API first
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.client: Union[Anthropic, Any] = Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
            self.provider = "anthropic"
        else:
            # Fall back to Vertex AI
            try:
                from anthropic import AnthropicVertex

                # Support both VERTEX_PROJECT_ID and ANTHROPIC_VERTEX_PROJECT_ID
                # (Claude Code uses ANTHROPIC_VERTEX_PROJECT_ID)
                project_id = os.environ.get("VERTEX_PROJECT_ID") or os.environ.get(
                    "ANTHROPIC_VERTEX_PROJECT_ID"
                )
                region = os.environ.get("VERTEX_REGION", "us-east5")

                if not project_id:
                    raise ValueError(
                        "Neither ANTHROPIC_API_KEY nor VERTEX_PROJECT_ID is set. "
                        "Please configure one of:\n"
                        "  - ANTHROPIC_API_KEY for Anthropic API\n"
                        "  - VERTEX_PROJECT_ID (or ANTHROPIC_VERTEX_PROJECT_ID) "
                        "for Google Vertex AI (also run: gcloud auth application-default login)"
                    )

                self.client = AnthropicVertex(project_id=project_id, region=region)
                self.provider = "vertex"
            except ImportError as e:
                raise ImportError(
                    "Vertex AI dependencies not installed. Install with: "
                    'pip install "anthropic[vertex]" google-cloud-aiplatform'
                ) from e

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Invoke Claude with validation failure context.

        The SDK automatically provides built-in tools for investigation
        and fixing. We don't specify which tools - let the SDK decide.

        Args:
            system_prompt: Explains validation failures to Claude
            user_message: Current validation results

        Returns:
            Response dict with content and tool_calls
        """
        # Create messages
        messages: list[MessageParam] = [
            cast(MessageParam, {"role": "user", "content": user_message})
        ]

        # Invoke Claude Code Agent SDK
        # SDK automatically provides whatever tools it wants
        # Type ignore needed due to Union[Anthropic, Any] client type
        response = self.client.messages.create(  # type: ignore[misc]
            model=self.model,
            max_tokens=8192,  # Reasonable default for investigation tasks
            system=system_prompt,
            messages=messages,
            tool_choice={"type": "auto"},
        )

        # Extract tool calls from response
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(
                    {
                        "tool": block.name,
                        "input": block.input,
                        "output": getattr(block, "output", None),
                    }
                )

        return {
            "content": response.content,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason,
        }
