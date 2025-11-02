"""Conditional edge functions for graph routing.

This module contains edge functions that determine routing paths
in the convergence state graph based on validation results and
attempt tracking.
"""

from typing import Literal

from alphanso.graph.state import ConvergenceState

# Type alias for possible routing decisions
EdgeDecision = Literal["end_success", "end_failure", "retry"]


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
