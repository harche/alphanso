"""Callable validator for executing Python functions as validators.

This module provides a validator that executes async Python callables,
enabling function-based validation alongside command-based validators.
"""

import logging
from collections.abc import Callable
from typing import Any

from alphanso.graph.state import ValidationResult
from alphanso.utils.callable import run_callable_async
from alphanso.validators.base import Validator

logger = logging.getLogger(__name__)


class CallableValidator(Validator):
    """Validator that executes an async Python callable.

    This validator runs a user-provided async function to perform validation,
    treating exceptions as failures and normal returns as success.

    Attributes:
        name: Human-readable validator name
        callable: Async function to execute
        timeout: Maximum execution time in seconds
        kwargs: Keyword arguments to pass to the callable
    """

    def __init__(
        self,
        name: str,
        callable: Callable[..., Any],
        timeout: float = 600.0,
        **kwargs: Any,
    ) -> None:
        """Initialize callable validator.

        Args:
            name: Human-readable name for this validator
            callable: Async function to execute (must be async def)
            timeout: Maximum execution time in seconds (default: 10 minutes)
            **kwargs: Keyword arguments to pass to the callable
        """
        super().__init__(name, timeout)
        self.callable = callable
        self.kwargs = kwargs

    async def avalidate(self) -> ValidationResult:
        """Run callable validation asynchronously.

        Executes the callable with the provided kwargs. Exceptions are treated
        as validation failures, normal returns as success.

        Returns:
            ValidationResult with success status and details
        """
        logger.info(f"Running callable validator: {self.name}")

        # Execute callable with timeout and error handling
        result = await run_callable_async(
            self.callable,
            timeout=self.timeout,
            **self.kwargs,
        )

        # Convert SubprocessResult to ValidationResult
        return ValidationResult(
            validator_name=self.name,
            success=result["success"],
            output=result["output"],
            stderr=result["stderr"],
            exit_code=result["exit_code"],
            duration=result["duration"],
            timestamp=0.0,  # Will be set by Validator.arun()
            metadata={},
        )
