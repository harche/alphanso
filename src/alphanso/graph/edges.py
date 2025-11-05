"""Conditional edge functions for graph routing.

This module contains edge functions that determine routing paths
in the convergence state graph based on validation results and
attempt tracking.
"""

from typing import Literal

from alphanso.graph.state import ConvergenceState

# Type alias for possible routing decisions from decide node
EdgeDecision = Literal["end_success", "end_failure", "retry"]

# Type alias for pre-actions routing
PreActionDecision = Literal["continue_to_validate", "end_pre_action_failure"]

# Type alias for main script routing
MainScriptDecision = Literal["end_success", "continue_to_validate"]


def should_continue(state: ConvergenceState) -> EdgeDecision:
    """Determine next step based on validation results.

    This is the core routing function for the convergence loop.
    It decides whether to:
    - End successfully (all validators passed)
    - End with failure (max attempts reached)
    - Retry (validators failed but attempts remain)

    Args:
        state: Current convergence state with validation results

    Returns:
        "end_success" - All validators passed, workflow complete
        "end_failure" - Max attempts reached without success
        "retry" - Validators failed, continue to next attempt

    Flow:
        validate → decide → should_continue() →
            ├─ "end_success" → END (success=True)
            ├─ "end_failure" → END (success=False)
            └─ "retry" → increment_attempt → validate (loop)

    Examples:
        >>> state = {"success": True, "attempt": 0, "max_attempts": 10}
        >>> should_continue(state)
        'end_success'

        >>> state = {"success": False, "attempt": 9, "max_attempts": 10}
        >>> should_continue(state)
        'end_failure'

        >>> state = {"success": False, "attempt": 2, "max_attempts": 10}
        >>> should_continue(state)
        'retry'
    """
    # Success - all validators passed
    if state["success"]:
        return "end_success"

    # Max attempts reached - give up
    # Note: attempt is 0-indexed, so attempt 9 means 10th attempt
    if state["attempt"] >= state["max_attempts"] - 1:
        return "end_failure"

    # Validators failed but attempts remain - retry
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
