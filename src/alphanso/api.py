"""Public API for Alphanso framework.

This module provides the main programmatic interface for using Alphanso.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from alphanso.config.schema import ConvergenceConfig
from alphanso.graph.builder import create_convergence_graph
from alphanso.graph.state import ConvergenceState
from alphanso.utils.logging import is_logging_configured, setup_logging

logger = logging.getLogger(__name__)


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
    system_prompt_content: str | None = None,
    env_vars: dict[str, str] | None = None,
    working_directory: str | Path | None = None,
    log_level: int = logging.INFO,
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
        log_level: Logging level for API users. Only used if logging not already
                  configured. Defaults to logging.INFO. Use logging.DEBUG for
                  detailed diagnostics.

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
    # Setup logging if not already configured
    # This ensures API users get logging output even if they don't call setup_logging()
    if not is_logging_configured():
        setup_logging(level=log_level)

    logger.info("=" * 70)
    logger.info(f"Starting convergence: {config.name}")
    logger.info("=" * 70)

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

    logger.info(f"Working directory: {working_dir_str}")
    logger.info(f"Max attempts: {config.max_attempts}")
    logger.info(f"Pre-actions: {len(config.pre_actions)}")
    logger.info(f"Validators: {len(config.validators)}")

    # Create initial state
    initial_state: ConvergenceState = {
        "pre_actions_completed": False,
        "pre_actions_config": [
            {"command": action.command, "description": action.description}
            for action in config.pre_actions
        ],
        "pre_action_results": [],
        "main_script_config": (
            {
                "command": config.main_script.command,
                "description": config.main_script.description,
                "timeout": config.main_script.timeout,
            }
            if config.main_script
            else {}
        ),
        "main_script_succeeded": False,
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
    logger.info("Creating convergence state graph...")
    graph = create_convergence_graph()

    logger.info("Executing convergence loop...")
    final_state = graph.invoke(initial_state)

    # Determine overall success
    # Success = main script succeeded (we trust its exit code)
    pre_actions_succeeded = not final_state.get("pre_actions_failed", False)
    main_script_succeeded = final_state.get("main_script_succeeded", False)
    overall_success = pre_actions_succeeded and main_script_succeeded

    # Build result
    result: ConvergenceResult = {
        "success": overall_success,
        "pre_action_results": final_state["pre_action_results"],
        "config_name": config.name,
        "working_directory": final_state["working_directory"],
    }

    logger.info("=" * 70)
    if overall_success:
        logger.info(f"✅ Convergence completed successfully - main script succeeded")
    elif not pre_actions_succeeded:
        failed_count = sum(1 for r in final_state["pre_action_results"] if not r["success"])
        logger.error(f"❌ Pre-actions failed ({failed_count} failure(s)) - workflow terminated")
    else:
        logger.error(f"❌ Main script failed after {final_state.get('attempt', 0) + 1} attempt(s)")
    logger.info("=" * 70)

    return result
