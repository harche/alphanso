"""Graph builder for Alphanso convergence loop.

This module provides functions to create and compile the LangGraph state graph
for the convergence workflow.
"""

from typing import TypeAlias

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from alphanso.graph.edges import should_continue
from alphanso.graph.nodes import (
    decide_node,
    increment_attempt_node,
    pre_actions_node,
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

    The graph structure with STEP 3 retry loop:

    START → pre_actions → validate → decide → {end_success, end_failure, retry}
                            ↑                           │
                            └─ increment_attempt ←──────┘

    Conditional routing from decide node:
    - "end_success": All validators passed → END (success)
    - "end_failure": Max attempts reached → END (failure)
    - "retry": Validators failed, attempts remain → increment_attempt → validate

    Returns:
        Compiled StateGraph ready for execution with retry loop

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
        ...     "working_directory": "."
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

    # Add nodes
    graph.add_node("pre_actions", pre_actions_node)
    graph.add_node("validate", validate_node)
    graph.add_node("decide", decide_node)
    graph.add_node("increment_attempt", increment_attempt_node)  # NEW: STEP 3

    # Add linear edges (setup phase)
    graph.add_edge(START, "pre_actions")
    graph.add_edge("pre_actions", "validate")
    graph.add_edge("validate", "decide")

    # Add conditional edges (STEP 3: retry loop logic)
    # The should_continue() function returns one of:
    # - "end_success": validators passed → END
    # - "end_failure": max attempts reached → END
    # - "retry": validators failed, try again → increment_attempt
    graph.add_conditional_edges(
        "decide",
        should_continue,
        {
            "end_success": END,
            "end_failure": END,
            "retry": "increment_attempt",
        },
    )

    # Add retry loop edge (STEP 3: completes the cycle)
    # After incrementing attempt, go back to validate
    graph.add_edge("increment_attempt", "validate")

    # Compile and return
    return graph.compile()
