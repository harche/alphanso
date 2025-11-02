"""Public API for Alphanso framework.

This module provides the main programmatic interface for using Alphanso.
Both CLI and library users should use these functions.
"""

from datetime import datetime
from pathlib import Path
from typing import TypedDict

from alphanso.config.schema import ConvergenceConfig
from alphanso.graph.nodes import pre_actions_node
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
    config_path: str | Path,
    env_vars: dict[str, str] | None = None,
) -> ConvergenceResult:
    """Run Alphanso convergence loop with the given configuration.

    This is the main entry point for using Alphanso programmatically.
    The CLI uses this same function internally.

    Args:
        config_path: Path to the YAML configuration file
        env_vars: Optional environment variables for substitution in pre-actions.
                 If CURRENT_TIME is not provided, it will be added automatically.

    Returns:
        ConvergenceResult with success status and pre-action results

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
        pydantic.ValidationError: If config doesn't match schema

    Example:
        >>> from alphanso.api import run_convergence
        >>> result = run_convergence(
        ...     config_path="config.yaml",
        ...     env_vars={"K8S_TAG": "v1.35.0"}
        ... )
        >>> if result["success"]:
        ...     print("All pre-actions succeeded!")
    """
    # Convert to Path object
    config_path_obj = Path(config_path)

    # Initialize env_vars if not provided
    if env_vars is None:
        env_vars = {}

    # Add default CURRENT_TIME if not provided
    if "CURRENT_TIME" not in env_vars:
        env_vars["CURRENT_TIME"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load configuration (may raise FileNotFoundError, YAMLError, ValidationError)
    config = ConvergenceConfig.from_yaml(config_path_obj)

    # Create initial state
    state: ConvergenceState = {
        "pre_actions_completed": False,
        "pre_actions_config": [
            {"command": action.command, "description": action.description}
            for action in config.pre_actions
        ],
        "pre_action_results": [],
        "env_vars": env_vars,
        "attempt": 0,
        "max_attempts": config.max_attempts,
        "success": False,
        "working_directory": str(config_path_obj.parent.absolute()),
    }

    # Execute pre-actions
    updates = pre_actions_node(state)

    # Merge updates into state (since pre_actions_node returns partial updates)
    final_state = {**state, **updates}

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
