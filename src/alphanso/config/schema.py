"""Configuration schema for Alphanso using Pydantic models.

This module defines the configuration structure for the entire framework,
including pre-actions, validators, and convergence settings.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class PreActionConfig(BaseModel):
    """Configuration for a single pre-action.

    Pre-actions are commands that run once before the convergence loop starts.

    Attributes:
        command: Shell command to execute
        description: Human-readable description of what this action does
    """

    command: str = Field(..., min_length=1, description="Shell command to execute")
    description: str = Field(default="", description="Description of the action")

    @model_validator(mode="after")
    def default_description(self) -> "PreActionConfig":
        """Use command as default description if not provided."""
        if not self.description:
            self.description = self.command
        return self


class MainScriptConfig(BaseModel):
    """Configuration for the main script.

    The main script is the primary goal of the workflow. It will be retried
    until it succeeds or max_attempts is reached. Validators only run when
    the main script fails, to verify the environment is healthy before retrying.

    Attributes:
        command: Shell command to execute
        description: Human-readable description of what this script does
        timeout: Maximum execution time in seconds (default: 600)
    """

    command: str = Field(..., min_length=1, description="Shell command to execute")
    description: str = Field(default="", description="Description of the script")
    timeout: float = Field(
        default=600.0, ge=1.0, description="Timeout in seconds"
    )

    @model_validator(mode="after")
    def default_description(self) -> "MainScriptConfig":
        """Use command as default description if not provided."""
        if not self.description:
            self.description = self.command
        return self


class ClaudeAgentConfig(BaseModel):
    """Configuration for Claude Agent SDK.

    The Claude Agent SDK provides production-ready AI agents with
    automatic context management, tools, and session handling.

    Attributes:
        model: Claude model identifier
        system_prompt: Custom system prompt content (populated from system_prompt_file)
        system_prompt_file: Optional path to file containing custom system prompt
    """

    model: str = Field(
        default="claude-sonnet-4-5@20250929",
        description="Claude model identifier (Vertex AI format)",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Custom system prompt content defining agent's role and task",
    )
    system_prompt_file: str | None = Field(
        default=None,
        description="Path to file containing custom system prompt defining agent's role and task",
    )


class OpenAIAgentConfig(BaseModel):
    """Configuration for OpenAI Agents SDK.

    The OpenAI Agents SDK provides lightweight agent building with
    built-in agent loops, handoffs, and guardrails.

    Attributes:
        model: OpenAI model identifier
    """

    model: str = Field(
        default="gpt-4",
        description="OpenAI model identifier",
    )


class AgentConfig(BaseModel):
    """Configuration for the AI Agent.

    Supports multiple agent types:
    - claude-agent-sdk: Claude Agent SDK for production agents
    - openai-agent-sdk: OpenAI Agents SDK with handoffs and guardrails

    Attributes:
        type: Agent SDK type
        claude: Configuration for Claude Agent SDK (when type='claude-agent-sdk')
        openai: Configuration for OpenAI Agents SDK (when type='openai-agent-sdk')
    """

    type: str = Field(
        default="claude-agent-sdk",
        description="Agent SDK type (claude-agent-sdk, openai-agent-sdk)",
    )
    claude: ClaudeAgentConfig = Field(
        default_factory=ClaudeAgentConfig,
        description="Claude Agent SDK configuration",
    )
    openai: OpenAIAgentConfig = Field(
        default_factory=OpenAIAgentConfig,
        description="OpenAI Agents SDK configuration",
    )


class ValidatorConfig(BaseModel):
    """Configuration for a single validator.

    Validators are conditions checked by the framework (build, test, conflicts).
    They are NOT tools for the AI agent.

    Attributes:
        type: Validator type (command, git-conflict)
        name: Human-readable validator name
        timeout: Maximum execution time in seconds
        command: Shell command (for type='command')
        capture_lines: Number of output lines to capture (for type='command')
    """

    type: str = Field(..., description="Validator type (command, git-conflict)")
    name: str = Field(..., description="Human-readable validator name")
    timeout: float = Field(default=600.0, ge=1.0, description="Timeout in seconds")
    command: str | None = Field(
        default=None, description="Shell command (for command validator)"
    )
    capture_lines: int = Field(
        default=100, ge=1, description="Lines to capture (for command validator)"
    )


class RetryStrategyConfig(BaseModel):
    """Configuration for retry strategy.

    Attributes:
        type: Type of retry strategy (e.g., 'hybrid')
        max_tracked_failures: Maximum number of failures to track for targeted retry
    """

    type: str = Field(
        default="hybrid",
        description="Retry strategy type",
    )
    max_tracked_failures: int = Field(
        default=10,
        ge=1,
        description="Max failures to track for targeted retry",
    )


class ConvergenceConfig(BaseModel):
    """Main configuration for Alphanso convergence loop.

    This is the root configuration object that encompasses all settings
    for running the convergence framework.

    Attributes:
        name: Name/description of this convergence configuration
        max_attempts: Maximum number of convergence loop iterations
        pre_actions: List of pre-actions to run before the loop
        main_script: Optional main script to retry until it succeeds
        validators: List of validators to run in the convergence loop
        agent: Agent configuration
        retry_strategy: Retry strategy configuration
        working_directory: Working directory for execution
    """

    name: str = Field(..., min_length=1, description="Configuration name")
    max_attempts: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum convergence attempts",
    )
    pre_actions: list[PreActionConfig] = Field(
        default_factory=list,
        description="Pre-actions to run before convergence loop",
    )
    main_script: MainScriptConfig | None = Field(
        default=None,
        description="Main script to retry until it succeeds (optional)",
    )
    validators: list[ValidatorConfig] = Field(
        default_factory=list,
        description="Validators to run in the convergence loop",
    )
    agent: AgentConfig = Field(
        default_factory=AgentConfig,
        description="Claude Agent configuration",
    )
    retry_strategy: RetryStrategyConfig = Field(
        default_factory=RetryStrategyConfig,
        description="Retry strategy configuration",
    )
    working_directory: str = Field(
        default=".",
        description="Working directory for command execution",
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ConvergenceConfig":
        """Load configuration from a YAML file.

        Handles system_prompt_file processing BEFORE validation:
        - Reads file referenced by system_prompt_file
        - Replaces with system_prompt field containing file content
        - Removes system_prompt_file before validation

        Args:
            path: Path to YAML configuration file

        Returns:
            Parsed ConvergenceConfig instance

        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML is invalid
            pydantic.ValidationError: If the config doesn't match schema

        Example:
            >>> config = ConvergenceConfig.from_yaml("rebase.yaml")
            >>> print(config.name)
            'Kubernetes Rebase'
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path_obj) as f:
            data = yaml.safe_load(f)

        # Process system_prompt_file BEFORE validation
        if "agent" in data and "claude" in data["agent"]:
            claude_config = data["agent"]["claude"]

            if "system_prompt_file" in claude_config:
                prompt_file = claude_config["system_prompt_file"]
                prompt_path = Path(prompt_file)

                # Resolve relative to config file location
                if not prompt_path.is_absolute():
                    prompt_path = path_obj.parent / prompt_path

                # Read file and populate system_prompt field
                if not prompt_path.exists():
                    raise FileNotFoundError(
                        f"System prompt file not found: {prompt_path}"
                    )

                with open(prompt_path) as f:
                    claude_config["system_prompt"] = f.read()

                # Keep system_prompt_file in config for reference

        return cls.model_validate(data)

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to a YAML file.

        Args:
            path: Path where YAML file should be written

        Example:
            >>> config = ConvergenceConfig(name="My Config")
            >>> config.to_yaml("config.yaml")
        """
        path_obj = Path(path)
        with open(path_obj, "w") as f:
            yaml.dump(
                self.model_dump(mode="json", exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
