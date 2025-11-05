"""Conditional edge functions for graph routing.

This module contains edge functions that determine routing paths
in the convergence state graph based on validation results and
attempt tracking.
"""

from typing import Literal

from alphanso.graph.state import ConvergenceState

# Type alias for possible routing decisions from decide node
EdgeDecision = Literal["validators_passed", "end_failure", "retry"]

# Type alias for pre-actions routing
PreActionDecision = Literal["continue_to_validate", "end_pre_action_failure"]

# Type alias for main script routing
MainScriptDecision = Literal["end_success", "continue_to_validate"]


def should_continue(state: ConvergenceState) -> EdgeDecision:
    """Determine next step based on validation results.

    This is the core routing function for the convergence loop.
    It decides whether to:
    - Retry main script (all validators passed, environment is healthy)
    - End with failure (max attempts reached)
    - Retry with AI fix (validators failed but attempts remain)

    Args:
        state: Current convergence state with validation results

    Returns:
        "validators_passed" - All validators passed, retry main_script immediately
        "end_failure" - Max attempts reached without success
        "retry" - Validators failed, need AI fix before retrying main_script

    Flow:
        validate → decide → should_continue() →
            ├─ "validators_passed" → increment_attempt → run_main_script (skip AI fix)
            ├─ "end_failure" → END (max attempts reached)
            └─ "retry" → increment_attempt → ai_fix → run_main_script

    Examples:
        >>> state = {"success": True, "attempt": 0, "max_attempts": 10}
        >>> should_continue(state)
        'validators_passed'

        >>> state = {"success": False, "attempt": 9, "max_attempts": 10}
        >>> should_continue(state)
        'end_failure'

        >>> state = {"success": False, "attempt": 2, "max_attempts": 10}
        >>> should_continue(state)
        'retry'
    """
    # Max attempts reached - give up
    # Note: attempt is 0-indexed, so attempt 9 means 10th attempt
    if state["attempt"] >= state["max_attempts"] - 1:
        return "end_failure"

    # Validators passed - environment is healthy, retry main script without AI fix
    if state["success"]:
        return "validators_passed"

    # Validators failed but attempts remain - need AI fix before retrying
    return "retry"


def check_pre_actions(state: ConvergenceState) -> PreActionDecision:
    """Determine whether to continue or exit after pre-actions.

    This routing function checks if pre-actions succeeded or failed.
    If any pre-action failed, the workflow terminates immediately.
    Otherwise, it proceeds to validation.

    Args:
        state: Current convergence state with pre-action results

    Returns:
        "continue_to_validate" - All pre-actions succeeded, proceed to validation
        "end_pre_action_failure" - At least one pre-action failed, terminate workflow

    Flow:
        pre_actions → check_pre_actions() →
            ├─ "continue_to_validate" → validate
            └─ "end_pre_action_failure" → END (with error)

    Examples:
        >>> state = {"pre_actions_failed": False}
        >>> check_pre_actions(state)
        'continue_to_validate'

        >>> state = {"pre_actions_failed": True}
        >>> check_pre_actions(state)
        'end_pre_action_failure'
    """
    if state.get("pre_actions_failed", False):
        return "end_pre_action_failure"
    return "continue_to_validate"


def check_main_script(state: ConvergenceState) -> MainScriptDecision:
    """Determine whether to exit or continue after main script execution.

    This routing function checks if the main script succeeded.
    If the script succeeded, we trust its exit code and end with success.
    If the script failed, we proceed to validators to check environment health.

    Args:
        state: Current convergence state with main_script_succeeded flag

    Returns:
        "end_success" - Main script succeeded, workflow complete
        "continue_to_validate" - Main script failed, run validators to enable fixes

    Flow:
        run_main_script → check_main_script() →
            ├─ "end_success" → END (script succeeded)
            └─ "continue_to_validate" → validate (script failed, check environment)

    Examples:
        >>> state = {"main_script_succeeded": True}
        >>> check_main_script(state)
        'end_success'

        >>> state = {"main_script_succeeded": False}
        >>> check_main_script(state)
        'continue_to_validate'
    """
    if state.get("main_script_succeeded", False):
        return "end_success"
    return "continue_to_validate"
