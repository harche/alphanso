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

    print("\n" + "=" * 70)
    print("NODE: pre_actions")
    print("=" * 70)
    print("Running pre-actions to set up environment...")
    print()

    results: list[PreActionResult] = []

    # Get environment variables and working directory from state
    env_vars = state.get("env_vars", {})
    working_dir = state.get("working_directory")

    # Add common variables from state
    if working_dir:
        env_vars.setdefault("WORKING_DIR", working_dir)

    # Run each pre-action
    for idx, action_config in enumerate(state.get("pre_actions_config", []), 1):
        pre_action = PreAction(
            command=action_config.get("command", ""),
            description=action_config.get("description", ""),
        )

        # Show what we're running
        print(f"[{idx}/{len(state.get('pre_actions_config', []))}] {pre_action.description}")

        result = pre_action.run(env_vars, working_dir=working_dir)
        results.append(result)

        # Show result
        if result["success"]:
            print(f"     ✅ Success")
            if result["output"]:
                # Show first line of output if available
                first_line = result["output"].strip().split("\n")[0]
                if first_line:
                    print(f"     │ {first_line}")
        else:
            print(f"     ❌ Failed")
            if result["stderr"]:
                print(f"     │ {result['stderr'][:200]}")
        print()

    # Return state updates (LangGraph will merge these)
    return {
        "pre_actions_completed": True,
        "pre_action_results": results,
    }


def validate_node(state: ConvergenceState) -> dict[str, Any]:
    """Run validators to check current state.

    This is a placeholder for STEP 1. In STEP 2, this will:
    - Execute all configured validators (build, test, conflict checks, etc.)
    - Capture results and failures
    - Update validation_results and failed_validators

    For now, it simply marks validation as successful.

    Args:
        state: Current convergence state

    Returns:
        Updated state with validation results

    Example:
        >>> state = {"attempt": 0}
        >>> updates = validate_node(state)
        >>> updates["success"]
        True
    """
    print("\n" + "=" * 70)
    print("NODE: validate")
    print("=" * 70)
    print("Running validators (placeholder - STEP 2 will implement)...")
    print("✅ Validation PASSED (all validators will be added in STEP 2)")
    print()

    # Placeholder: Always succeed for STEP 1
    # STEP 2 will implement actual validator execution
    return {
        "success": True,
        "validation_results": [],
        "failed_validators": [],
    }


def decide_node(state: ConvergenceState) -> dict[str, Any]:
    """Decide whether to continue, retry, or end.

    This is a placeholder for STEP 1. In STEP 3, this will implement
    conditional logic to determine the next step based on validation results.

    For now, it returns an empty dict (no state updates).

    Args:
        state: Current convergence state

    Returns:
        Empty dict (no updates for STEP 1)

    Example:
        >>> state = {"success": True}
        >>> updates = decide_node(state)
        >>> updates
        {}
    """
    print("\n" + "=" * 70)
    print("NODE: decide")
    print("=" * 70)
    print("Making decision (placeholder - STEP 3 will implement retry logic)...")
    print("✅ Decision: END (no retry loop yet)")
    print("=" * 70)
    print()

    # Placeholder: No decision logic for STEP 1
    # STEP 3 will implement conditional edges and retry logic
    return {}


# Additional node functions will be added in future steps:
# - ai_fix_node (STEP 5) - Invoke Claude agent to fix failures
# - increment_attempt_node (STEP 3) - Increment attempt counter
