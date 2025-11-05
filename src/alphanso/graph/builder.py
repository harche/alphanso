"""Graph builder for Alphanso convergence loop.

This module provides functions to create and compile the LangGraph state graph
for the convergence workflow.
"""

from typing import TypeAlias

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from alphanso.graph.edges import check_main_script, check_pre_actions, should_continue
from alphanso.graph.nodes import (
    ai_fix_node,
    decide_node,
    increment_attempt_node,
    pre_actions_node,
    run_main_script_node,
    validate_node,
)
from alphanso.graph.state import ConvergenceState

# Type alias for the compiled convergence graph
# CompiledStateGraph generic parameters: [StateT, ContextT, InputT, OutputT]
# - StateT: Internal state type (ConvergenceState)
# - ContextT: Context passed to nodes (None - we don't use context)
# - InputT: Input type when invoking graph (ConvergenceState)
# - OutputT: Output type from graph execution (ConvergenceState)
ConvergenceGraph: TypeAlias = CompiledStateGraph[
    ConvergenceState, None, ConvergenceState, ConvergenceState
]


def create_convergence_graph() -> ConvergenceGraph:
    """Create and compile the convergence state graph.

    The graph structure: Script-centric workflow where main script is retried
    until it succeeds. Validators only run when script fails to verify environment.

    START → pre_actions → run_main_script → check_main_script() → {END success, validate}
                ↓                                                          ↓
         check_pre_actions()                                         validate → decide
                ↓                                                          ↑         ↓
           {run_main_script, END}                           ai_fix ← increment ← retry
                                                                         ↓
                                                              run_main_script (loop)

    Workflow:
    1. pre_actions: One-time setup (e.g., clone repo, setup remotes)
       - If any fail → END with error
    2. run_main_script: Execute the main goal script (e.g., rebase)
       - If succeeds → END with success
       - If fails → run validators
    3. validators: Check environment health (build, tests)
       - If all pass → increment → retry main_script (environment is healthy)
       - If any fail → increment → AI fixes → retry main_script
    4. Loop until main_script succeeds or max_attempts reached

    Conditional routing:
    - check_pre_actions(): all passed → run_main_script | any failed → END
    - check_main_script(): succeeded → END | failed → validate
    - should_continue(): validators passed → increment → run_main_script |
                        max attempts → END |
                        validators failed → increment → ai_fix → run_main_script

    Returns:
        Compiled StateGraph ready for execution with AI-powered retry loop

    Example:
        >>> graph = create_convergence_graph()
        >>> initial_state: ConvergenceState = {
        ...     "pre_actions_completed": False,
        ...     "pre_actions_config": [
        ...         {"command": "echo 'hello'", "description": "Test"}
        ...     ],
        ...     "env_vars": {},
        ...     "attempt": 0,
        ...     "max_attempts": 10,
        ...     "success": False,
        ...     "working_directory": ".",
        ...     "agent_config": {"model": "claude-sonnet-4-5@20250929"}
        ... }
        >>> final_state = graph.invoke(initial_state)
        >>> final_state["success"]
        True
    """
    # Create state graph with ConvergenceState schema
    # Explicit annotation needed for mypy to verify return type matches ConvergenceGraph
    graph: StateGraph[ConvergenceState, None, ConvergenceState, ConvergenceState] = (
        StateGraph(ConvergenceState)
    )

    # Add all nodes
    graph.add_node("pre_actions", pre_actions_node)
    graph.add_node("run_main_script", run_main_script_node)
    graph.add_node("validate", validate_node)
    graph.add_node("decide", decide_node)
    graph.add_node("increment_attempt", increment_attempt_node)
    graph.add_node("ai_fix", ai_fix_node)

    # START → pre_actions
    graph.add_edge(START, "pre_actions")

    # pre_actions → check_pre_actions() → {run_main_script, END}
    # If pre-actions fail, end immediately; otherwise run main script
    graph.add_conditional_edges(
        "pre_actions",
        check_pre_actions,
        {
            "continue_to_validate": "run_main_script",
            "end_pre_action_failure": END,
        },
    )

    # run_main_script → check_main_script() → {END success, validate}
    # If script succeeds, end with success
    # If script fails, run validators to check environment health
    graph.add_conditional_edges(
        "run_main_script",
        check_main_script,
        {
            "end_success": END,
            "continue_to_validate": "validate",
        },
    )

    # validate → decide
    graph.add_edge("validate", "decide")

    # decide → should_continue() → {validators_passed, END failure, retry}
    # Based on validator results:
    #   - all pass → retry main_script (environment healthy)
    #   - max attempts → END
    #   - some fail → ai_fix then retry main_script
    graph.add_conditional_edges(
        "decide",
        should_continue,
        {
            "validators_passed": "increment_attempt",
            "end_failure": END,
            "retry": "increment_attempt",
        },
    )

    # increment_attempt → conditional based on whether validators passed or failed
    # If validators passed: go directly to run_main_script (skip AI fix)
    # If validators failed: go to ai_fix first
    def route_after_increment(state: ConvergenceState) -> str:
        """Route after increment_attempt based on validator results.

        If validators all passed, skip AI fix and retry main script directly.
        If validators failed, apply AI fix before retrying.
        """
        if state.get("success", False):
            return "run_main_script"
        return "ai_fix"

    graph.add_conditional_edges(
        "increment_attempt",
        route_after_increment,
        {
            "run_main_script": "run_main_script",
            "ai_fix": "ai_fix",
        },
    )

    # ai_fix → run_main_script (after fixing issues)
    graph.add_edge("ai_fix", "run_main_script")

    # Compile and return
    return graph.compile()
