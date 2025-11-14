"""Base class for all validators.

Validators are conditions we check (build, test, conflicts, etc.).
They are RUN BY THE FRAMEWORK in the validate_node.
They are NOT tools for the AI agent.
"""

import logging
import time
from abc import ABC, abstractmethod

from alphanso.graph.state import ValidationResult

logger = logging.getLogger(__name__)


class Validator(ABC):
    """Base class for all validators.

    Validators execute checks (build, test, conflicts) and return structured results.
    The framework runs validators in validate_node - they are not exposed to the AI.

    Attributes:
        name: Human-readable validator name
        timeout: Maximum execution time in seconds
    """

    def __init__(self, name: str, timeout: float = 600.0) -> None:
        """Initialize validator.

        Args:
            name: Human-readable name for this validator
            timeout: Maximum execution time in seconds (default: 10 minutes)
        """
        self.name = name
        self.timeout = timeout

    @abstractmethod
    async def avalidate(self) -> ValidationResult:
        """Run validation asynchronously and return result.

        This is the primary method that must be implemented by subclasses to perform
        the actual validation logic using async I/O (async subprocess calls, etc.).

        Returns:
            ValidationResult with success status and details

        Raises:
            Any exception will be caught by arun() and converted to a failed result
        """
        pass

    def validate(self) -> ValidationResult:
        """Run validation synchronously by calling async version.

        This is a convenience wrapper that calls avalidate() using asyncio.run().
        Subclasses should implement avalidate() only - this sync version is
        automatically provided.

        Returns:
            ValidationResult with success status and details

        Raises:
            Any exception will be caught by run() and converted to a failed result
        """
        import asyncio

        # Run the async avalidate() method in sync context
        return asyncio.run(self.avalidate())

    def run(self) -> ValidationResult:
        """Run validator with timing and error handling.

        This is the public interface that validate_node calls. It wraps the
        subclass's validate() method with timing and exception handling.

        Returns:
            ValidationResult with timing information and error handling
        """
        start = time.time()
        try:
            result = self.validate()
            # Add timing information
            result["duration"] = time.time() - start
            result["timestamp"] = start
            return result
        except Exception as e:
            # Convert exception to failed validation result
            logger.debug(f"Validator '{self.name}' raised exception: {e}", exc_info=True)
            return ValidationResult(
                validator_name=self.name,
                success=False,
                output="",
                stderr=str(e),
                exit_code=None,
                duration=time.time() - start,
                timestamp=start,
                metadata={},
            )

    async def arun(self) -> ValidationResult:
        """Run validator asynchronously with timing and error handling.

        Async version of run() for use in async applications (e.g., Kubernetes operators).
        This wraps the subclass's avalidate() method with timing and exception handling.

        Returns:
            ValidationResult with timing information and error handling
        """
        start = time.time()
        try:
            result = await self.avalidate()
            # Add timing information
            result["duration"] = time.time() - start
            result["timestamp"] = start
            return result
        except Exception as e:
            # Convert exception to failed validation result
            logger.debug(
                f"Validator '{self.name}' raised exception (async): {e}", exc_info=True
            )
            return ValidationResult(
                validator_name=self.name,
                success=False,
                output="",
                stderr=str(e),
                exit_code=None,
                duration=time.time() - start,
                timestamp=start,
                metadata={},
            )
