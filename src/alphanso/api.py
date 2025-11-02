"""Public API for Alphanso framework.

This module provides the main programmatic interface for using Alphanso.
"""

from datetime import datetime
from pathlib import Path
from typing import TypedDict

from alphanso.config.schema import ConvergenceConfig
from alphanso.graph.builder import create_convergence_graph
from alphanso.graph.state import ConvergenceState


class PreActionResultDict(TypedDict):
    """Result from a single pre-action."""

    action: str
    success: bool
    output: str
    stderr: str
    exit_code: int | None
    duration: float


class ConvergenceResult(TypedDict):
    """Result from running convergence."""

    success: bool
    pre_action_results: list[PreActionResultDict]
    config_name: str
    working_directory: str


def run_convergence(
    config: ConvergenceConfig,
    system_prompt_content: str,
    env_vars: dict[str, str] | None = None,
    working_directory: str | Path | None = None,
) -> ConvergenceResult:
    """Run Alphanso convergence loop with the given configuration.

    This is the main entry point for using Alphanso programmatically.

    Args:
        config: ConvergenceConfig object with workflow configuration
        system_prompt_content: System prompt content defining agent's role and task.
                              CLI loads this from config.agent.claude.system_prompt_file.
                              Direct API users should provide the content directly.
        env_vars: Optional environment variables for substitution in pre-actions.
                 If CURRENT_TIME is not provided, it will be added automatically.
        working_directory: Optional working directory for command execution.
                          Defaults to config.working_directory if not provided.

    Returns:
        ConvergenceResult with success status and pre-action results

    Example:
        >>> from alphanso.api import run_convergence
        >>> from alphanso.config.schema import ConvergenceConfig, PreActionConfig
        >>>
        >>> # Create config programmatically
        >>> config = ConvergenceConfig(
        ...     name="My Workflow",
        ...     max_attempts=10,
        ...     pre_actions=[
        ...         PreActionConfig(
        ...             command="echo 'Hello'",
        ...             description="Greeting"
        ...         )
        ...     ]
        ... )
        >>>
        >>> # Run convergence
        >>> result = run_convergence(
        ...     config=config,
        ...     env_vars={"K8S_TAG": "v1.35.0"}
        ... )
        >>>
        >>> if result["success"]:
        ...     print("All steps succeeded!")
    """
    # Initialize env_vars if not provided
    if env_vars is None:
        env_vars = {}

    # Add default CURRENT_TIME if not provided
    if "CURRENT_TIME" not in env_vars:
        env_vars["CURRENT_TIME"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Determine working directory
    if working_directory is None:
        working_directory = config.working_directory
    working_dir_str = str(Path(working_directory).absolute())

    # Create initial state
    initial_state: ConvergenceState = {
        "pre_actions_completed": False,
        "pre_actions_config": [
            {"command": action.command, "description": action.description}
            for action in config.pre_actions
        ],
        "pre_action_results": [],
        "validators_config": [
            {
                "type": validator.type,
                "name": validator.name,
                "command": validator.command,
                "timeout": validator.timeout,
                "capture_lines": validator.capture_lines,
            }
            for validator in config.validators
        ],
        "validation_results": [],
        "failed_validators": [],
        "failure_history": [],
        "env_vars": env_vars,
        "attempt": 0,
        "max_attempts": config.max_attempts,
        "success": False,
        "working_directory": working_dir_str,
        "agent_config": {"model": config.agent.claude.model},
        "system_prompt_content": system_prompt_content,
    }

    # Create and execute convergence graph
    graph = create_convergence_graph()
    final_state = graph.invoke(initial_state)

    # Determine overall success (all pre-actions succeeded)
    all_success = all(
        result["success"] for result in final_state["pre_action_results"]
    )

    # Build result
    result: ConvergenceResult = {
        "success": all_success,
        "pre_action_results": final_state["pre_action_results"],
        "config_name": config.name,
        "working_directory": final_state["working_directory"],
    }

    return result
