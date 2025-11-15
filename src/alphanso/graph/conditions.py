"""Condition registry for conditional edge routing.

This module provides a registry for mapping condition names to their implementations,
enabling dynamic conditional edge construction from configuration.
"""

import logging
from collections.abc import Callable

from alphanso.graph.state import ConvergenceState

logger = logging.getLogger(__name__)


class ConditionRegistry:
    """Registry for conditional edge functions.

    The registry maps condition names (e.g., 'check_pre_actions', 'should_continue')
    to their corresponding routing functions. This enables dynamic conditional edge
    construction from configuration.

    Example:
        >>> ConditionRegistry.register("my_condition", my_condition_func)
        >>> func = ConditionRegistry.get("my_condition")
        >>> names = ConditionRegistry.list_conditions()
        ['check_pre_actions', 'check_main_script', 'should_continue', 'my_condition']
    """

    _conditions: dict[str, Callable[[ConvergenceState], str]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        func: Callable[[ConvergenceState], str],
    ) -> None:
        """Register a condition function.

        Args:
            name: Unique identifier for the condition
            func: Function implementing the routing logic
                  Must have signature: (state: ConvergenceState) -> str
                  Returns a string indicating which edge to follow

        Raises:
            ValueError: If name is already registered

        Example:
            >>> def my_condition(state: ConvergenceState) -> str:
            ...     return "success" if state.get("success") else "failure"
            >>> ConditionRegistry.register("my_condition", my_condition)
        """
        if name in cls._conditions:
            logger.warning(f"Condition '{name}' is already registered. Overwriting.")

        cls._conditions[name] = func
        logger.debug(f"Registered condition: {name}")

    @classmethod
    def get(cls, name: str) -> Callable[[ConvergenceState], str]:
        """Get condition function by name.

        Args:
            name: Condition identifier

        Returns:
            Condition function

        Raises:
            ValueError: If name is not registered

        Example:
            >>> func = ConditionRegistry.get("should_continue")
            >>> decision = func(state)
        """
        if name not in cls._conditions:
            available = ", ".join(cls.list_conditions())
            raise ValueError(f"Unknown condition: '{name}'. Available conditions: {available}")

        return cls._conditions[name]

    @classmethod
    def list_conditions(cls) -> list[str]:
        """List all registered condition names.

        Returns:
            List of registered condition identifiers

        Example:
            >>> ConditionRegistry.list_conditions()
            ['check_pre_actions', 'check_main_script', 'should_continue']
        """
        return sorted(cls._conditions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a condition is registered.

        Args:
            name: Condition name to check

        Returns:
            True if the condition is registered, False otherwise

        Example:
            >>> ConditionRegistry.is_registered("should_continue")
            True
            >>> ConditionRegistry.is_registered("unknown_condition")
            False
        """
        return name in cls._conditions

    @classmethod
    def clear(cls) -> None:
        """Clear all registered conditions.

        This is primarily useful for testing. Use with caution.
        """
        cls._conditions.clear()
        logger.debug("Cleared all registered conditions")


def register_builtin_conditions() -> None:
    """Register all built-in condition functions.

    This function imports and registers the default condition implementations
    from the edges module. It should be called during module initialization.
    """
    # Import here to avoid circular dependencies
    from alphanso.graph.edges import check_main_script, check_pre_actions, should_continue

    ConditionRegistry.register("check_pre_actions", check_pre_actions)
    ConditionRegistry.register("check_main_script", check_main_script)
    ConditionRegistry.register("should_continue", should_continue)

    logger.info(f"Registered {len(ConditionRegistry.list_conditions())} built-in conditions")


# Register built-in conditions when module is imported
register_builtin_conditions()
