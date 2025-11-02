"""Graph nodes for Alphanso convergence loop.

This module contains the node functions that make up the convergence state graph.
For STEP 0, we implement the pre_actions_node.
"""

from typing import Any

from alphanso.actions.pre_actions import PreAction, PreActionResult
from alphanso.graph.state import ConvergenceState


def pre_actions_node(state: ConvergenceState) -> dict[str, Any]:
    """Run pre-actions before entering convergence loop.

    Pre-actions are setup commands that run once (e.g., git merge, container setup,
    go mod tidy). They execute sequentially, and failures are captured but don't
    stop execution - they'll be caught in the subsequent validation phase.

    Args:
        state: Current convergence state

    Returns:
        Updated state with pre_actions_completed=True and pre_action_results

    Example:
        >>> state = {
        ...     "pre_actions_completed": False,
        ...     "pre_actions_config": [
        ...         {"command": "git fetch upstream", "description": "Fetch upstream"},
        ...         {"command": "git merge upstream/${TAG}", "description": "Merge tag"}
        ...     ],
        ...     "env_vars": {"TAG": "v1.35.0"}
        ... }
        >>> new_state = pre_actions_node(state)
        >>> new_state["pre_actions_completed"]
        True
    """
    # Skip if pre-actions already completed (idempotent)
    if state.get("pre_actions_completed", False):
        return {}

    results: list[PreActionResult] = []

    # Get environment variables and working directory from state
    env_vars = state.get("env_vars", {})
    working_dir = state.get("working_directory")

    # Add common variables from state
    if working_dir:
        env_vars.setdefault("WORKING_DIR", working_dir)

    # Run each pre-action
    for action_config in state.get("pre_actions_config", []):
        pre_action = PreAction(
            command=action_config.get("command", ""),
            description=action_config.get("description", ""),
        )

        result = pre_action.run(env_vars, working_dir=working_dir)
        results.append(result)

        # Log but continue even on failures
        # The framework will catch these in the validation phase
        if not result["success"]:
            # In a real implementation, this would use proper logging
            print(f"⚠️  Pre-action failed: {result['action']}")
            if result["stderr"]:
                print(f"   {result['stderr'][:200]}")

    # Return state updates (LangGraph will merge these)
    return {
        "pre_actions_completed": True,
        "pre_action_results": results,
    }


# Additional node functions will be added in future steps:
# - validate_node (STEP 2)
# - decide_node (STEP 3)
# - ai_fix_node (STEP 5)
# - increment_attempt_node (STEP 3)
