"""Graph builder for Alphanso convergence loop.

This module provides functions to create and compile the LangGraph state graph
for the convergence workflow.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from alphanso.config.schema import EdgeConfig, WorkflowConfig
from alphanso.graph.conditions import ConditionRegistry
from alphanso.graph.edges import check_main_script, check_pre_actions, should_continue
from alphanso.graph.nodes import (
    ai_fix_node,
    decide_node,
    increment_attempt_node,
    pre_actions_node,
    run_main_script_node,
    validate_node,
)
from alphanso.graph.registry import NodeRegistry
from alphanso.graph.state import ConvergenceState

logger = logging.getLogger(__name__)

# Type alias for the compiled convergence graph
# CompiledStateGraph generic parameters: [StateT, ContextT, InputT, OutputT]
# - StateT: Internal state type (ConvergenceState)
# - ContextT: Context passed to nodes (None - we don't use context)
# - InputT: Input type when invoking graph (ConvergenceState)
# - OutputT: Output type from graph execution (ConvergenceState)
type ConvergenceGraph = CompiledStateGraph[
    ConvergenceState, None, ConvergenceState, ConvergenceState
]


def create_convergence_graph(workflow_config: WorkflowConfig | None = None) -> ConvergenceGraph:
    """Create and compile the convergence state graph.

    Creates either a custom workflow from configuration or the default hardcoded topology.

    Args:
        workflow_config: Optional custom workflow configuration. If None, uses default topology.

    Returns:
        Compiled StateGraph ready for execution with AI-powered retry loop

    Example:
        >>> # Use default topology
        >>> graph = create_convergence_graph()
        >>> # Use custom topology
        >>> custom_workflow = WorkflowConfig(
        ...     nodes=[...],
        ...     edges=[...]
        ... )
        >>> graph = create_convergence_graph(custom_workflow)
    """
    if workflow_config is None:
        logger.info("Building default convergence graph topology")
        return build_default_topology()

    logger.info("Building custom convergence graph from workflow configuration")
    return build_from_config(workflow_config)


def build_default_topology() -> ConvergenceGraph:
    """Build the default hardcoded topology for backward compatibility.

    The graph structure: Script-centric workflow where main script is retried
    until it succeeds. When script fails, AI sees the error immediately and attempts
    a fix, then validators verify the fix worked.

    START → pre_actions → run_main_script → check_main_script() → {END success, increment}
                ↓                                                          ↓
         check_pre_actions()                                          ai_fix
                ↓                                                          ↓
           {run_main_script, END}                                     validate → decide
                                                                          ↑         ↓
                                                              run_main_script ← {validators_passed, retry}
                                                                                     ↓
                                                                                END (max attempts)

    Workflow:
    1. pre_actions: One-time setup (e.g., clone repo, setup remotes)
       - If any fail → END with error
    2. run_main_script: Execute the main goal script (e.g., rebase)
       - If succeeds → END with success
       - If fails → increment attempt → AI sees error and attempts fix
    3. ai_fix: AI analyzes main script error and applies fix
       - AI gets main script error output (stderr, stdout, exit code)
       - AI investigates and fixes using SDK tools
    4. validators: Verify AI's fix worked (build, tests, etc.)
       - If all pass → increment → retry main_script (fix was successful)
       - If any fail → increment → AI refines fix (gets validator failures)
    5. Loop until main_script succeeds or max_attempts reached

    Conditional routing:
    - check_pre_actions(): all passed → run_main_script | any failed → END
    - check_main_script(): succeeded → END | failed → increment → ai_fix
    - should_continue(): validators passed → increment → run_main_script |
                        max attempts → END |
                        validators failed → increment → ai_fix (refine)

    Returns:
        Compiled StateGraph with default topology

    Example:
        >>> graph = build_default_topology()
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
        ...     "main_script_config": {
        ...         "command": "echo 'test'",
        ...         "description": "Test script",
        ...         "timeout": 600
        ...     },
        ...     "agent_config": {"model": "claude-sonnet-4-5@20250929"}
        ... }
        >>> final_state = graph.invoke(initial_state)
        >>> final_state["main_script_succeeded"]
        True
    """
    # Create state graph with ConvergenceState schema
    # Explicit annotation needed for mypy to verify return type matches ConvergenceGraph
    graph: StateGraph[ConvergenceState, None, ConvergenceState, ConvergenceState] = StateGraph(
        ConvergenceState
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

    # run_main_script → check_main_script() → {END success, ai_fix}
    # If script succeeds, end with success
    # If script fails, go to AI for analysis and fix
    graph.add_conditional_edges(
        "run_main_script",
        check_main_script,
        {
            "end_success": END,
            "continue_to_ai_fix": "ai_fix",
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

    # increment_attempt → conditional based on validator results
    # If validators passed: go directly to run_main_script (environment is healthy)
    # If validators failed: go to ai_fix first (need to fix validation failures)
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

    # ai_fix → validate (AI fixes first, then validators verify the fix)
    graph.add_edge("ai_fix", "validate")

    # Compile and return
    return graph.compile()


def build_from_config(workflow_config: WorkflowConfig) -> ConvergenceGraph:
    """Build graph dynamically from workflow configuration.

    Args:
        workflow_config: Workflow configuration defining nodes and edges

    Returns:
        Compiled StateGraph with custom topology

    Raises:
        ValueError: If topology is invalid

    Example:
        >>> from alphanso.config.schema import WorkflowConfig, NodeConfig, EdgeConfig
        >>> workflow = WorkflowConfig(
        ...     nodes=[
        ...         NodeConfig(type="pre_actions", name="setup"),
        ...         NodeConfig(type="run_main_script", name="main"),
        ...         NodeConfig(type="ai_fix", name="fix"),
        ...     ],
        ...     edges=[
        ...         EdgeConfig(from_node="START", to_node="setup"),
        ...         EdgeConfig(from_node="setup", to_node="main"),
        ...         EdgeConfig(from_node="main", to_node=["END", "fix"], condition="check_main_script"),
        ...         EdgeConfig(from_node="fix", to_node="main"),
        ...     ]
        ... )
        >>> graph = build_from_config(workflow)
    """
    # Validate topology first
    validate_topology(workflow_config)

    # Create state graph
    graph: StateGraph[ConvergenceState, None, ConvergenceState, ConvergenceState] = StateGraph(
        ConvergenceState
    )

    # Add nodes from config
    logger.info(f"Adding {len(workflow_config.nodes)} nodes to graph")
    for node_config in workflow_config.nodes:
        node_func = NodeRegistry.get(node_config.type)
        graph.add_node(node_config.name, node_func)
        logger.debug(f"  Added node: {node_config.name} (type={node_config.type})")

    # Add edges from config
    logger.info(f"Adding {len(workflow_config.edges)} edges to graph")
    for edge_config in workflow_config.edges:
        _add_edge_to_graph(graph, edge_config)

    # Set entry point by adding edge from START
    entry_point = workflow_config.entry_point or workflow_config.nodes[0].name
    logger.info(f"Setting entry point: {entry_point}")
    graph.add_edge(START, entry_point)

    # Compile and return
    logger.info("Compiling custom workflow graph")
    return graph.compile()


def _add_edge_to_graph(
    graph: StateGraph[ConvergenceState, None, ConvergenceState, ConvergenceState],
    edge_config: "EdgeConfig",
) -> None:
    """Add an edge to the graph based on configuration.

    Args:
        graph: StateGraph to add edge to
        edge_config: Edge configuration

    Raises:
        ValueError: If edge configuration is invalid
    """
    from_node = edge_config.from_node
    to_node = edge_config.to_node
    condition = edge_config.condition

    # Convert string "END" to actual END constant
    if isinstance(to_node, str) and to_node == "END":
        to_node = END
    elif isinstance(to_node, list):
        to_node = [END if t == "END" else t for t in to_node]

    # Skip edges from START - entry point is set separately
    if from_node == "START":
        logger.debug("  Skipping START edge (entry point will be set separately)")
        return

    if condition:
        # Conditional edge
        condition_func = ConditionRegistry.get(condition)

        if isinstance(to_node, list):
            # Multiple targets - build mapping
            # Infer mapping from target names (assumes condition returns matching strings)
            mapping = {target: target for target in to_node}
            graph.add_conditional_edges(from_node, condition_func, mapping)
            logger.debug(f"  Added conditional edge: {from_node} --[{condition}]--> {to_node}")
        else:
            # Single target with condition
            graph.add_conditional_edges(from_node, condition_func, {to_node: to_node})
            logger.debug(f"  Added conditional edge: {from_node} --[{condition}]--> {to_node}")
    else:
        # Unconditional edge
        if isinstance(to_node, list):
            raise ValueError(
                f"Edge from '{from_node}' has multiple targets {to_node} "
                f"but no condition. Use a condition for multi-target edges."
            )
        graph.add_edge(from_node, to_node)
        logger.debug(f"  Added edge: {from_node} --> {to_node}")


def validate_topology(workflow_config: WorkflowConfig) -> None:
    """Validate workflow topology for correctness.

    Args:
        workflow_config: Workflow configuration to validate

    Raises:
        ValueError: If topology is invalid

    Checks:
    - All node types are registered
    - Node names are unique
    - Edges reference valid nodes
    - Conditions are registered
    - Entry point is valid
    """
    # Check all nodes are registered
    for node in workflow_config.nodes:
        if not NodeRegistry.is_registered(node.type):
            available = ", ".join(NodeRegistry.list_types())
            raise ValueError(f"Unknown node type: '{node.type}'. Available types: {available}")

    # Check node names are unique
    names = [n.name for n in workflow_config.nodes]
    if len(names) != len(set(names)):
        duplicates = [name for name in names if names.count(name) > 1]
        raise ValueError(f"Duplicate node names found: {set(duplicates)}")

    # Check at least one node
    if not workflow_config.nodes:
        raise ValueError("Workflow must have at least one node")

    # Build set of valid node names (includes special START/END)
    node_names = set(names) | {"START", "END"}

    # Check edges reference valid nodes
    for edge in workflow_config.edges:
        if edge.from_node not in node_names:
            raise ValueError(
                f"Edge from '{edge.from_node}' references unknown node. "
                f"Valid nodes: {sorted(node_names)}"
            )

        targets = [edge.to_node] if isinstance(edge.to_node, str) else edge.to_node
        for target in targets:
            if target not in node_names:
                raise ValueError(
                    f"Edge to '{target}' references unknown node. "
                    f"Valid nodes: {sorted(node_names)}"
                )

    # Check conditions are registered
    for edge in workflow_config.edges:
        if edge.condition and not ConditionRegistry.is_registered(edge.condition):
            available = ", ".join(ConditionRegistry.list_conditions())
            raise ValueError(
                f"Unknown condition: '{edge.condition}'. Available conditions: {available}"
            )

    # Check entry point is valid
    if workflow_config.entry_point and workflow_config.entry_point not in names:
        raise ValueError(
            f"Entry point '{workflow_config.entry_point}' is not a valid node name. "
            f"Valid nodes: {names}"
        )

    logger.debug("Topology validation passed")


def register_condition(name: str, func: Callable[[ConvergenceState], str]) -> None:
    """Register a custom condition function.

    Helper function to register conditions with the ConditionRegistry.

    Args:
        name: Condition identifier
        func: Condition function with signature (state: ConvergenceState) -> str
    """
    ConditionRegistry.register(name, func)


def register_node(
    node_type: str, func: Callable[[ConvergenceState], Awaitable[dict[str, Any]]]
) -> None:
    """Register a custom node implementation.

    Helper function to register nodes with the NodeRegistry.

    Args:
        node_type: Node type identifier
        func: Node function with signature async (state: ConvergenceState) -> dict[str, Any]
    """
    NodeRegistry.register(node_type, func)
