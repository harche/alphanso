"""State schema for Alphanso convergence graph.

This module defines the state structure that flows through the LangGraph
convergence loop.
"""

from typing import Any, TypedDict

from alphanso.actions.pre_actions import PreActionResult


class ValidationResult(TypedDict):
    """Result from executing a validator.

    Validators are conditions we check (build, test, conflicts, etc.).
    They are run by the framework in the validate_node, NOT by the AI agent.

    Attributes:
        validator_name: Name of the validator that was run
        success: Whether validation passed (exit code 0 or equivalent)
        output: Captured stdout (last N chars, truncated)
        stderr: Captured stderr (last N chars, truncated)
        exit_code: Process exit code (None if exception occurred)
        duration: Time taken to execute in seconds
        timestamp: Unix timestamp when validation started
        metadata: Additional validator-specific data (e.g., failing packages)
    """

    validator_name: str
    success: bool
    output: str
    stderr: str
    exit_code: int | None
    duration: float
    timestamp: float
    metadata: dict[str, Any]


class ConvergenceState(TypedDict, total=False):
    """State for the convergence loop.

    This TypedDict defines all state that flows through the convergence graph.
    All fields are optional (total=False) since nodes return partial updates
    that are merged into the state by LangGraph.

    Attributes:
        # Pre-actions (run once at start)
        pre_actions_completed: Whether pre-actions have been run
        pre_action_results: Results from pre-action executions
        pre_actions_config: Configuration for pre-actions (commands to run)

        # Loop control
        attempt: Current convergence loop iteration number
        max_attempts: Maximum allowed iterations
        success: Whether convergence was successful

        # Validation (run by framework, NOT AI)
        validation_results: Results from current validation attempt
        failed_validators: Names of validators that failed
        failure_history: History of failures across all attempts

        # AI interaction (investigation and fixing tools)
        agent_config: Agent configuration (model, etc.)
        agent_session_id: Claude Agent SDK session ID
        agent_tool_calls: History of AI tool calls made
        agent_messages: Conversation history with AI
        ai_response: Response from most recent AI invocation
        system_prompt_content: System prompt content defining agent's role and task

        # Configuration
        validators_config: Configuration for validators
        ai_tools_config: Configuration for AI tools
        retry_strategy: Retry strategy type (hybrid, full, targeted)

        # Environment
        working_directory: Working directory for command execution
        env_vars: Environment variables for variable substitution

        # Metadata
        start_time: Unix timestamp when convergence started
        total_duration: Total time taken in seconds
    """

    # Pre-actions (run once at start)
    pre_actions_completed: bool
    pre_action_results: list[PreActionResult]
    pre_actions_config: list[dict[str, str]]

    # Loop control
    attempt: int
    max_attempts: int
    success: bool

    # Validation (run by framework in validate_node)
    validation_results: list[ValidationResult]
    failed_validators: list[str]
    failure_history: list[list[ValidationResult]]

    # AI interaction (tools for investigation and fixing)
    agent_config: dict[str, Any]
    agent_session_id: str | None
    agent_tool_calls: list[dict[str, Any]]
    agent_messages: list[str]
    ai_response: dict[str, Any]
    system_prompt_content: str

    # Configuration
    validators_config: list[dict[str, Any]]
    ai_tools_config: dict[str, Any]
    retry_strategy: str

    # Environment
    working_directory: str
    env_vars: dict[str, str]

    # Metadata
    start_time: float
    total_duration: float
