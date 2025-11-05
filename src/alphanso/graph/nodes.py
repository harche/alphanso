"""Graph nodes for Alphanso convergence loop.

This module contains the node functions that make up the convergence state graph.
"""

import logging
from typing import Any

from alphanso.actions.pre_actions import PreAction, PreActionResult
import subprocess
import time
from alphanso.agent.client import ConvergenceAgent
from alphanso.agent.prompts import build_fix_prompt, build_user_message
from alphanso.graph.state import ConvergenceState
from alphanso.validators import (
    CommandValidator,
    GitConflictValidator,
    TestSuiteValidator,
    Validator,
)

logger = logging.getLogger(__name__)


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
        elif validator_type == "test-suite":
            validators.append(
                TestSuiteValidator(
                    name=config.get("name", "Test Suite"),
                    command=config.get("command", ""),
                    timeout=config.get("timeout", 1800.0),
                    capture_lines=config.get("capture_lines", 200),
                    working_directory=working_dir,
                )
            )
        else:
            raise ValueError(
                f"Unknown validator type: {validator_type}. "
                f"Supported types: command, git-conflict, test-suite"
            )

    return validators


def pre_actions_node(state: ConvergenceState) -> dict[str, Any]:
    """Run pre-actions before entering convergence loop.

    Pre-actions are setup commands that run once (e.g., git clone, mkdir, setup scripts).
    They execute sequentially in the CURRENT DIRECTORY (not working_directory), which
    allows them to create/setup the working directory itself. If any pre-action fails,
    the workflow will terminate with an error and not proceed to validation.

    IMPORTANT: Pre-actions run in current directory, NOT in working_directory.
    This design allows pre-actions to:
    - Create the working directory (e.g., git clone)
    - Setup the environment before entering working_directory
    - Run setup scripts from the project root

    Main script and validators will run in working_directory.

    Args:
        state: Current convergence state

    Returns:
        Updated state with pre_actions_completed=True, pre_action_results, and pre_actions_failed flag

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
        logger.debug("Pre-actions already completed, skipping")
        return {}

    logger.info("=" * 70)
    logger.info("NODE: pre_actions")
    logger.info("=" * 70)
    logger.info("Running pre-actions to set up environment...")
    logger.debug(f"📍 Entering pre_actions_node | pre_actions_completed={state.get('pre_actions_completed', False)}")

    results: list[PreActionResult] = []

    # Get environment variables and working directory from state
    env_vars = state.get("env_vars", {})
    working_dir = state.get("working_directory")

    # IMPORTANT: Pre-actions run in CURRENT DIRECTORY, not working_directory
    # This allows pre-actions to create/setup the working directory itself
    # (e.g., setup.sh can clone into kubernetes/, mkdir, etc.)
    logger.info(f"Pre-actions run in: current directory (where config file is)")
    logger.info(f"Main script/validators will run in: {working_dir or 'current directory'}")
    logger.info(f"Environment variables: {list(env_vars.keys())}")

    # Add common variables from state
    if working_dir:
        env_vars.setdefault("WORKING_DIR", working_dir)

    # Run each pre-action
    all_succeeded = True
    for idx, action_config in enumerate(state.get("pre_actions_config", []), 1):
        pre_action = PreAction(
            command=action_config.get("command", ""),
            description=action_config.get("description", ""),
        )

        # Show what we're running
        logger.info(f"[{idx}/{len(state.get('pre_actions_config', []))}] {pre_action.description}")

        # Pre-actions run in current directory (None = current directory)
        # NOT in working_directory, so they can create/setup that directory
        result = pre_action.run(env_vars, working_dir=None)
        results.append(result)

        # Show result
        if result["success"]:
            logger.info(f"     ✅ Success")
            if result["output"]:
                # Show first line of output if available
                first_line = result["output"].strip().split("\n")[0]
                if first_line:
                    logger.info(f"     │ {first_line}")
                # Log full output at debug level
                logger.debug(f"Full output: {result['output']}")
        else:
            all_succeeded = False
            logger.error(f"     ❌ Failed")
            if result["stderr"]:
                logger.error(f"     │ {result['stderr'][:200]}")
            logger.debug(f"Full stderr: {result['stderr']}")

    # Check if any pre-actions failed
    if not all_succeeded:
        logger.error("=" * 70)
        logger.error("❌ Pre-actions FAILED - workflow will terminate")
        logger.error("=" * 70)
        logger.debug(f"📤 Exiting pre_actions_node | pre_actions_failed=True, {len(results)} results")
        return {
            "pre_actions_completed": True,
            "pre_action_results": results,
            "pre_actions_failed": True,
        }

    # Return state updates (LangGraph will merge these)
    logger.debug(f"📤 Exiting pre_actions_node | Updating: pre_actions_completed=True, {len(results)} results")
    return {
        "pre_actions_completed": True,
        "pre_action_results": results,
        "pre_actions_failed": False,
    }


def run_main_script_node(state: ConvergenceState) -> dict[str, Any]:
    """Run the main script.

    The main script is the primary goal of the workflow. It will be retried
    until it succeeds or max_attempts is reached. This node executes the
    script and captures its result.

    Args:
        state: Current convergence state

    Returns:
        Updated state with main_script_result and main_script_succeeded flag

    Example:
        >>> state = {
        ...     "main_script_config": {
        ...         "command": "./ocp-rebase.sh --k8s-tag=v1.35.0",
        ...         "description": "Rebase OpenShift",
        ...         "timeout": 600
        ...     },
        ...     "working_directory": "/path/to/repo"
        ... }
        >>> new_state = run_main_script_node(state)
        >>> new_state["main_script_succeeded"]
        True
    """
    logger.info("=" * 70)
    logger.info("NODE: run_main_script")
    logger.info("=" * 70)

    # Get main script config
    script_config = state.get("main_script_config", {})
    working_dir = state.get("working_directory")
    attempt = state.get("attempt", 0)

    command = script_config.get("command", "")
    description = script_config.get("description", command)
    timeout = script_config.get("timeout", 600.0)

    logger.info(f"Running main script (attempt {attempt + 1}/{state.get('max_attempts', 10)})...")
    logger.info(f"Description: {description}")
    logger.info(f"Command: {command}")
    logger.info(f"Timeout: {timeout}s")
    logger.info(f"Working directory: {working_dir}")
    logger.info("")

    # Run the script with timing
    start = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
        )

        duration = time.time() - start
        success = result.returncode == 0

        # Log result
        if success:
            logger.info(f"✅ Main script SUCCEEDED ({duration:.2f}s)")
            if result.stdout:
                first_line = result.stdout.strip().split("\n")[0]
                if first_line:
                    logger.info(f"   │ {first_line[:80]}")
                logger.debug(f"Full stdout: {result.stdout}")
        else:
            logger.error(f"❌ Main script FAILED (exit code: {result.returncode}, {duration:.2f}s)")
            if result.stderr:
                first_error = result.stderr.strip().split("\n")[0]
                logger.error(f"   │ {first_error[:80]}")
            logger.info(f"Full stderr: {result.stderr}")

        from alphanso.graph.state import MainScriptResult
        script_result: MainScriptResult = {
            "command": command,
            "success": success,
            "output": result.stdout[-2000:],  # Last 2000 chars
            "stderr": result.stderr[-2000:],
            "exit_code": result.returncode,
            "duration": duration,
        }

        logger.debug(f"📤 Exiting run_main_script_node | success={success}")
        return {
            "main_script_result": script_result,
            "main_script_succeeded": success,
        }

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        logger.error(f"❌ Main script TIMED OUT after {timeout}s")

        from alphanso.graph.state import MainScriptResult
        script_result: MainScriptResult = {
            "command": command,
            "success": False,
            "output": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "exit_code": None,
            "duration": duration,
        }

        logger.debug(f"📤 Exiting run_main_script_node | timeout")
        return {
            "main_script_result": script_result,
            "main_script_succeeded": False,
        }

    except Exception as e:
        duration = time.time() - start
        logger.error(f"❌ Main script raised exception: {e}")
        logger.debug(f"Exception details:", exc_info=True)

        from alphanso.graph.state import MainScriptResult
        script_result: MainScriptResult = {
            "command": command,
            "success": False,
            "output": "",
            "stderr": str(e),
            "exit_code": None,
            "duration": duration,
        }

        logger.debug(f"📤 Exiting run_main_script_node | exception")
        return {
            "main_script_result": script_result,
            "main_script_succeeded": False,
        }


def validate_node(state: ConvergenceState) -> dict[str, Any]:
    """Run validators to check current state.

    Executes configured validators (build, test, conflict checks, etc.) in order
    until one fails or all pass. Stops immediately on first failure to allow
    AI agent to fix the issue without wasting time on subsequent validators.
    Validators are run by the framework to check conditions - they are NOT tools
    for the AI agent.

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
    logger.info("=" * 70)
    logger.info("NODE: validate")
    logger.info("=" * 70)
    logger.info("Running validators to check current state...")

    # Get validators configuration and working directory
    validators_config = state.get("validators_config", [])
    working_dir = state.get("working_directory")
    attempt = state.get("attempt", 0)

    logger.debug(f"📍 Entering validate_node | attempt={attempt}, validators={len(validators_config)}")

    # Handle case with no validators configured
    if not validators_config:
        logger.warning("⚠️  No validators configured - skipping validation")
        return {
            "success": True,
            "validation_results": [],
            "failed_validators": [],
        }

    # Create validator instances
    validators = create_validators(validators_config, working_dir)

    # Run each validator and collect results
    # IMPORTANT: Stop on first failure to call AI immediately with the error
    validation_results = []
    failed_validators = []

    for idx, validator in enumerate(validators, 1):
        logger.info(f"[{idx}/{len(validators)}] {validator.name}")

        result = validator.run()
        validation_results.append(result)

        # Show result
        if result["success"]:
            logger.info(f"     ✅ Success ({result['duration']:.2f}s)")
            if result["output"]:
                # Show first line of output if available
                first_line = result["output"].strip().split("\n")[0]
                if first_line:
                    logger.info(f"     │ {first_line[:80]}")
                # Log full output at debug level
                logger.debug(f"Full output: {result['output']}")
        else:
            logger.info(f"     ❌ Failed ({result['duration']:.2f}s)")
            failed_validators.append(validator.name)
            if result["stderr"]:
                # Show first line of error
                first_error = result["stderr"].strip().split("\n")[0]
                logger.info(f"     │ {first_error[:80]}")
            # Log full error at INFO level (users need to see it)
            logger.info(f"Full stderr: {result['stderr']}")

            # Stop on first failure - don't run remaining validators
            # This allows AI to fix the issue immediately
            logger.info(f"⚠️  Stopping validation after first failure (skipping {len(validators) - idx} remaining validator(s))")
            break

    # Determine overall success
    success = len(failed_validators) == 0

    if success:
        logger.info("✅ All validators PASSED")
    else:
        logger.info(f"❌ {len(failed_validators)} validator(s) FAILED:")
        for name in failed_validators:
            logger.info(f"   - {name}")

    # Update failure history if validators failed
    # This ensures every validation attempt is recorded, even the last one
    updated_history = list(state.get("failure_history", []))
    if not success:
        updated_history.append(validation_results)

    logger.debug(f"📤 Exiting validate_node | success={success}, failed={len(failed_validators)}, history_entries={len(updated_history)}")

    # TRACE: Full state dump for ultra-verbose diagnostics
    logger.trace(f"🔍 State dump after validation:\n{{\n  success: {success},\n  attempt: {state.get('attempt', 0)}/{state.get('max_attempts', 10)},\n  failed_validators: {failed_validators},\n  validation_results: {len(validation_results)} results,\n  failure_history: {len(updated_history)} entries\n}}")  # type: ignore

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
    logger.info("=" * 70)
    logger.info("NODE: decide")
    logger.info("=" * 70)

    # Show current state info
    success = state.get("success", False)
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 10)
    failed_validators = state.get("failed_validators", [])

    logger.debug(f"📍 Entering decide_node | success={success}, attempt={attempt}/{max_attempts}")

    if success:
        logger.info("✅ All validators passed")
        logger.info("   Decision: END with success")
        logger.debug("📤 Exiting decide_node | Routing: end_success")
    elif attempt >= max_attempts - 1:
        logger.info(f"⚠️  Max attempts reached ({attempt + 1}/{max_attempts})")
        logger.info(f"   Failed validators: {', '.join(failed_validators) if failed_validators else 'none'}")
        logger.info("   Decision: END with failure")
        logger.debug("📤 Exiting decide_node | Routing: end_failure")
    else:
        logger.info(f"❌ Validation failed (attempt {attempt + 1}/{max_attempts})")
        logger.info(f"   Failed validators: {', '.join(failed_validators)}")
        logger.info("   Decision: RETRY (increment attempt and re-validate)")
        logger.debug("📤 Exiting decide_node | Routing: retry -> increment_attempt")

    logger.info("=" * 70)

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
    logger.info("=" * 70)
    logger.info("NODE: increment_attempt")
    logger.info("=" * 70)

    new_attempt = state["attempt"] + 1
    failure_history = state.get("failure_history", [])

    logger.debug(f"📍 Entering increment_attempt_node | current_attempt={state['attempt']}, incrementing to {new_attempt}")

    logger.info(f"📊 Attempt {state['attempt'] + 1} → {new_attempt + 1}")
    logger.info(f"   Failed validators: {', '.join(state.get('failed_validators', []))}")
    logger.debug(f"   Failure history entries: {len(failure_history)}")
    logger.info("🔄 Retrying validation...")
    logger.info("=" * 70)

    logger.debug(f"📤 Exiting increment_attempt_node | Updated: attempt={new_attempt}")
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
    logger.info("=" * 70)
    logger.info("NODE: ai_fix")
    logger.info("=" * 70)
    logger.info("Invoking Claude agent to investigate and fix failures...")

    # Get agent configuration
    agent_config = state.get("agent_config", {})
    model = agent_config.get("model", "claude-sonnet-4-5@20250929")
    working_dir = state.get("working_directory")
    custom_prompt = state.get("system_prompt_content")
    failed_validators = state.get("failed_validators", [])

    logger.debug(f"📍 Entering ai_fix_node | failed_validators={failed_validators}, model={model}")

    # Initialize agent
    try:
        agent = ConvergenceAgent(
            model=model,
            working_directory=working_dir,
        )
        logger.info(f"✅ Agent initialized")
        logger.info(f"   Provider: {agent.provider}")
        logger.info(f"   Model: {agent.model}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        logger.debug(f"📤 Exiting ai_fix_node | Error during agent initialization")
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
        logger.info("🤖 Invoking Claude agent...")

        response = agent.invoke(system_prompt, user_message)

        logger.info(f"✅ Agent invocation completed")
        logger.info(f"   Stop reason: {response.get('stop_reason', 'unknown')}")
        logger.info(f"   Tool calls: {response.get('tool_call_count', 0)}")

        logger.debug(f"📤 Exiting ai_fix_node | Agent completed with {response.get('tool_call_count', 0)} tool calls")

        # TRACE: Full AI response dump for ultra-verbose diagnostics
        logger.trace(f"🔍 Full AI response dump:\n{{\n  content: {response.get('content', [])[:200]}{'...' if len(str(response.get('content', []))) > 200 else ''},\n  tool_call_count: {response.get('tool_call_count', 0)},\n  stop_reason: {response.get('stop_reason', 'unknown')}\n}}")  # type: ignore

        return {
            "ai_response": response,
        }
    except Exception as e:
        logger.error(f"❌ Agent invocation failed: {e}")
        logger.debug(f"📤 Exiting ai_fix_node | Error during agent invocation")
        return {
            "ai_response": {
                "error": str(e),
                "success": False,
            }
        }
