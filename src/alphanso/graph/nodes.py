"""Graph nodes for Alphanso convergence loop.

This module contains the node functions that make up the convergence state graph.
"""

from typing import Any

from alphanso.actions.pre_actions import PreAction, PreActionResult
from alphanso.graph.state import ConvergenceState
from alphanso.validators import CommandValidator, GitConflictValidator, Validator


def create_validators(
    validators_config: list[dict[str, Any]],
    working_dir: str | None = None,
) -> list[Validator]:
    """Create validator instances from configuration.

    Args:
        validators_config: List of validator configuration dictionaries
        working_dir: Working directory for validators

    Returns:
        List of instantiated Validator objects

    Raises:
        ValueError: If validator type is unknown

    Example:
        >>> config = [
        ...     {"type": "command", "name": "Build", "command": "make"},
        ...     {"type": "git-conflict", "name": "Conflicts"}
        ... ]
        >>> validators = create_validators(config, "/path/to/repo")
        >>> len(validators)
        2
    """
    validators: list[Validator] = []

    for config in validators_config:
        validator_type = config.get("type", "")

        if validator_type == "command":
            validators.append(
                CommandValidator(
                    name=config.get("name", "Unknown Command"),
                    command=config.get("command", ""),
                    timeout=config.get("timeout", 600.0),
                    capture_lines=config.get("capture_lines", 100),
                    working_dir=working_dir,
                )
            )
        elif validator_type == "git-conflict":
            validators.append(
                GitConflictValidator(
                    name=config.get("name", "Git Conflict Check"),
                    timeout=config.get("timeout", 10.0),
                    working_dir=working_dir,
                )
            )
        else:
            raise ValueError(
                f"Unknown validator type: {validator_type}. "
                f"Supported types: command, git-conflict"
            )

    return validators


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

    Executes all configured validators (build, test, conflict checks, etc.)
    and captures results. Validators are run by the framework to check
    conditions - they are NOT tools for the AI agent.

    Args:
        state: Current convergence state

    Returns:
        Updated state with validation results and success status

    Example:
        >>> state = {
        ...     "validators_config": [
        ...         {"type": "command", "name": "Build", "command": "make"}
        ...     ],
        ...     "working_directory": "/path/to/repo"
        ... }
        >>> updates = validate_node(state)
        >>> "success" in updates
        True
        >>> "validation_results" in updates
        True
    """
    print("\n" + "=" * 70)
    print("NODE: validate")
    print("=" * 70)
    print("Running validators to check current state...")
    print()

    # Get validators configuration and working directory
    validators_config = state.get("validators_config", [])
    working_dir = state.get("working_directory")

    # Handle case with no validators configured
    if not validators_config:
        print("⚠️  No validators configured - skipping validation")
        print()
        return {
            "success": True,
            "validation_results": [],
            "failed_validators": [],
        }

    # Create validator instances
    validators = create_validators(validators_config, working_dir)

    # Run each validator and collect results
    validation_results = []
    failed_validators = []

    for idx, validator in enumerate(validators, 1):
        print(f"[{idx}/{len(validators)}] {validator.name}")

        result = validator.run()
        validation_results.append(result)

        # Show result
        if result["success"]:
            print(f"     ✅ Success ({result['duration']:.2f}s)")
            if result["output"]:
                # Show first line of output if available
                first_line = result["output"].strip().split("\n")[0]
                if first_line:
                    print(f"     │ {first_line[:80]}")
        else:
            print(f"     ❌ Failed ({result['duration']:.2f}s)")
            failed_validators.append(validator.name)
            if result["stderr"]:
                # Show first line of error
                first_error = result["stderr"].strip().split("\n")[0]
                print(f"     │ {first_error[:80]}")
        print()

    # Determine overall success
    success = len(failed_validators) == 0

    if success:
        print("✅ All validators PASSED")
    else:
        print(f"❌ {len(failed_validators)} validator(s) FAILED:")
        for name in failed_validators:
            print(f"   - {name}")
    print()

    return {
        "success": success,
        "validation_results": validation_results,
        "failed_validators": failed_validators,
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
