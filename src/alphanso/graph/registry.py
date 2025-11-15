"""Node registry for workflow graph construction.

This module provides a registry for mapping node types to their implementations,
enabling dynamic graph construction from configuration.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from alphanso.graph.state import ConvergenceState

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Registry for workflow node types and their implementations.

    The registry maps node type strings (e.g., 'pre_actions', 'ai_fix') to
    their corresponding async function implementations. This enables dynamic
    graph construction from configuration.

    Example:
        >>> NodeRegistry.register("custom_node", my_custom_node_func)
        >>> func = NodeRegistry.get("custom_node")
        >>> types = NodeRegistry.list_types()
        ['pre_actions', 'run_main_script', 'validate', 'ai_fix', 'custom_node']
    """

    _nodes: dict[str, Callable[[ConvergenceState], Awaitable[dict[str, Any]]]] = {}

    @classmethod
    def register(
        cls,
        node_type: str,
        func: Callable[[ConvergenceState], Awaitable[dict[str, Any]]],
    ) -> None:
        """Register a node implementation.

        Args:
            node_type: Unique identifier for the node type
            func: Async function implementing the node logic
                  Must have signature: async (state: ConvergenceState) -> dict[str, Any]

        Raises:
            ValueError: If node_type is already registered

        Example:
            >>> async def my_node(state: ConvergenceState) -> dict[str, Any]:
            ...     return {"my_field": "value"}
            >>> NodeRegistry.register("my_node", my_node)
        """
        if node_type in cls._nodes:
            logger.warning(f"Node type '{node_type}' is already registered. Overwriting.")

        cls._nodes[node_type] = func
        logger.debug(f"Registered node type: {node_type}")

    @classmethod
    def get(cls, node_type: str) -> Callable[[ConvergenceState], Awaitable[dict[str, Any]]]:
        """Get node implementation by type.

        Args:
            node_type: Node type identifier

        Returns:
            Node implementation function

        Raises:
            ValueError: If node_type is not registered

        Example:
            >>> func = NodeRegistry.get("ai_fix")
            >>> result = await func(state)
        """
        if node_type not in cls._nodes:
            available = ", ".join(cls.list_types())
            raise ValueError(f"Unknown node type: '{node_type}'. Available types: {available}")

        return cls._nodes[node_type]

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered node types.

        Returns:
            List of registered node type identifiers

        Example:
            >>> NodeRegistry.list_types()
            ['pre_actions', 'run_main_script', 'validate', 'ai_fix', ...]
        """
        return sorted(cls._nodes.keys())

    @classmethod
    def is_registered(cls, node_type: str) -> bool:
        """Check if a node type is registered.

        Args:
            node_type: Node type to check

        Returns:
            True if the node type is registered, False otherwise

        Example:
            >>> NodeRegistry.is_registered("ai_fix")
            True
            >>> NodeRegistry.is_registered("unknown_node")
            False
        """
        return node_type in cls._nodes

    @classmethod
    def clear(cls) -> None:
        """Clear all registered nodes.

        This is primarily useful for testing. Use with caution.
        """
        cls._nodes.clear()
        logger.debug("Cleared all registered nodes")


def register_builtin_nodes() -> None:
    """Register all built-in node types.

    This function imports and registers the default node implementations
    from the nodes module. It should be called during module initialization.
    """
    # Import here to avoid circular dependencies
    from alphanso.graph.nodes import (
        ai_fix_node,
        decide_node,
        increment_attempt_node,
        pre_actions_node,
        run_main_script_node,
        validate_node,
    )

    NodeRegistry.register("pre_actions", pre_actions_node)
    NodeRegistry.register("run_main_script", run_main_script_node)
    NodeRegistry.register("validate", validate_node)
    NodeRegistry.register("ai_fix", ai_fix_node)
    NodeRegistry.register("increment_attempt", increment_attempt_node)
    NodeRegistry.register("decide", decide_node)

    logger.info(f"Registered {len(NodeRegistry.list_types())} built-in node types")


# Register built-in nodes when module is imported
register_builtin_nodes()
