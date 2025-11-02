"""Graph nodes for Alphanso convergence loop.

This module contains the node functions that make up the convergence state graph.
"""

from typing import Any

from alphanso.actions.pre_actions import PreAction, PreActionResult
from alphanso.agent.client import ConvergenceAgent
from alphanso.agent.prompts import build_fix_prompt, build_user_message
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

    # Update failure history if validators failed
    # This ensures every validation attempt is recorded, even the last one
    updated_history = list(state.get("failure_history", []))
    if not success:
        updated_history.append(validation_results)

    return {
        "success": success,
        "validation_results": validation_results,
        "failed_validators": failed_validators,
        "failure_history": updated_history,
    }


def decide_node(state: ConvergenceState) -> dict[str, Any]:
    """Decide whether to continue, retry, or end.

    This node is a pass-through for STEP 3. The actual routing decision
    is made by the should_continue() edge function based on validation
    results and attempt count.

    Args:
        state: Current convergence state

    Returns:
        Empty dict (no state updates needed - routing handled by edges)

    Flow:
        validate → decide → should_continue() →
            ├─ "end_success" → END (all validators passed)
            ├─ "end_failure" → END (max attempts reached)
            └─ "retry" → increment_attempt → validate (loop)

    Example:
        >>> state = {"success": True}
        >>> updates = decide_node(state)
        >>> updates
        {}
    """
    print("\n" + "=" * 70)
    print("NODE: decide")
    print("=" * 70)

    # Show current state info
    success = state.get("success", False)
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 10)
    failed_validators = state.get("failed_validators", [])

    if success:
        print("✅ All validators passed")
        print("   Decision: END with success")
    elif attempt >= max_attempts - 1:
        print(f"⚠️  Max attempts reached ({attempt + 1}/{max_attempts})")
        print(f"   Failed validators: {', '.join(failed_validators) if failed_validators else 'none'}")
        print("   Decision: END with failure")
    else:
        print(f"❌ Validation failed (attempt {attempt + 1}/{max_attempts})")
        print(f"   Failed validators: {', '.join(failed_validators)}")
        print("   Decision: RETRY (increment attempt and re-validate)")

    print("=" * 70)
    print()

    # No state updates - routing handled by should_continue() edge function
    return {}


def increment_attempt_node(state: ConvergenceState) -> dict[str, Any]:
    """Increment attempt counter for retry loop.

    This node runs after validation failures when retrying.
    It increments the attempt counter to track loop iterations.

    Note: Failure history is tracked by validate_node, not here.
    This ensures all validation attempts (including the last one)
    are recorded in failure_history.

    Args:
        state: Current convergence state with validation results

    Returns:
        Partial state update with incremented attempt

    Flow:
        validate (failed) → decide → retry → increment_attempt → validate

    Example:
        >>> state = {
        ...     "attempt": 0,
        ...     "validation_results": [{"validator_name": "test", "success": False}],
        ...     "failure_history": []
        ... }
        >>> updates = increment_attempt_node(state)
        >>> updates["attempt"]
        1
    """
    print("\n" + "=" * 70)
    print("NODE: increment_attempt")
    print("=" * 70)

    new_attempt = state["attempt"] + 1
    failure_history = state.get("failure_history", [])

    print(f"📊 Attempt {state['attempt'] + 1} → {new_attempt + 1}")
    print(f"   Failed validators: {', '.join(state.get('failed_validators', []))}")
    print(f"   Failure history entries: {len(failure_history)}")
    print("🔄 Retrying validation...")
    print("=" * 70)
    print()

    return {
        "attempt": new_attempt,
    }


def ai_fix_node(state: ConvergenceState) -> dict[str, Any]:
    """Invoke Claude agent to investigate and fix validation failures.

    This node is called when validators fail. It uses the Claude Agent SDK
    to analyze the validation failures and attempt to fix them using available
    tools (bash commands, file operations, etc.).

    The agent is given:
    - System prompt with context about failed validators and attempt history
    - User message with detailed validation failure information
    - Access to SDK tools for investigation and fixes

    Args:
        state: Current convergence state with validation failures

    Returns:
        Updated state with AI response metadata

    Flow:
        validate (failed) → decide → retry → increment_attempt → ai_fix → validate

    Example:
        >>> state = {
        ...     "attempt": 1,
        ...     "max_attempts": 5,
        ...     "failed_validators": ["Build"],
        ...     "validation_results": [{"validator_name": "Build", "success": False, ...}],
        ...     "failure_history": [...],
        ...     "agent_config": {"model": "claude-sonnet-4-5@20250929"},
        ...     "working_directory": "/path/to/repo"
        ... }
        >>> updates = ai_fix_node(state)
        >>> "ai_response" in updates
        True
    """
    print("\n" + "=" * 70)
    print("NODE: ai_fix")
    print("=" * 70)
    print("Invoking Claude agent to investigate and fix failures...")
    print()

    # Get agent configuration
    agent_config = state.get("agent_config", {})
    model = agent_config.get("model", "claude-sonnet-4-5@20250929")
    working_dir = state.get("working_directory")
    custom_prompt = state.get("system_prompt_content")

    # Initialize agent
    try:
        agent = ConvergenceAgent(
            model=model,
            working_directory=working_dir,
        )
        print(f"✅ Agent initialized")
        print(f"   Provider: {agent.provider}")
        print(f"   Model: {agent.model}")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        print()
        return {
            "ai_response": {
                "error": str(e),
                "success": False,
            }
        }

    # Build prompts
    system_prompt = build_fix_prompt(state, custom_prompt=custom_prompt)
    user_message = build_user_message(state)

    # Invoke agent
    try:
        print("🤖 Invoking Claude agent...")
        print()

        response = agent.invoke(system_prompt, user_message)

        print(f"✅ Agent invocation completed")
        print(f"   Stop reason: {response.get('stop_reason', 'unknown')}")
        print(f"   Tool calls: {response.get('tool_call_count', 0)}")
        print()

        return {
            "ai_response": response,
        }
    except Exception as e:
        print(f"❌ Agent invocation failed: {e}")
        print()
        return {
            "ai_response": {
                "error": str(e),
                "success": False,
            }
        }
