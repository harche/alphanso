"""State schema for Alphanso convergence graph.

This module defines the state structure that flows through the LangGraph
convergence loop.
"""

from typing import TypedDict

from alphanso.actions.pre_actions import PreActionResult


class ConvergenceState(TypedDict, total=False):
    """State for the convergence loop.

    This TypedDict defines all state that flows through the convergence graph.
    For STEP 0, we only define pre-action related fields. Additional fields
    will be added in subsequent steps.

    Attributes:
        pre_actions_completed: Whether pre-actions have been run
        pre_action_results: Results from pre-action executions
        pre_actions_config: Configuration for pre-actions (commands to run)
        attempt: Current convergence loop iteration number
        max_attempts: Maximum allowed iterations
        success: Whether convergence was successful
        working_directory: Working directory for command execution
        env_vars: Environment variables for variable substitution
    """

    # Pre-actions (run once at start)
    pre_actions_completed: bool
    pre_action_results: list[PreActionResult]
    pre_actions_config: list[dict[str, str]]

    # Loop control
    attempt: int
    max_attempts: int
    success: bool

    # Environment
    working_directory: str
    env_vars: dict[str, str]

    # Additional fields will be added in future steps:
    # - validation_results
    # - failed_validators
    # - failure_history
    # - agent_session_id
    # - agent_tool_calls
    # - agent_messages
    # - validators_config
    # - ai_tools_config
    # - retry_strategy
    # - start_time
    # - total_duration
