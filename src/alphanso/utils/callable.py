"""Async callable utilities for running Python functions.

This module provides async wrappers for executing Python callables, allowing
function-based workflows alongside command-based workflows in convergence tasks.
"""

import asyncio
import inspect
import io
import logging
import sys
import time
import traceback
from collections.abc import Callable
from typing import Any

from alphanso.utils.subprocess import SubprocessResult

logger = logging.getLogger(__name__)


def get_callable_metadata(func: Callable[..., Any]) -> dict[str, Any]:
    """Extract metadata from a callable for debugging and AI context.

    Args:
        func: The callable to extract metadata from

    Returns:
        Dictionary with function name, docstring, signature, and source info
    """
    metadata: dict[str, Any] = {
        "name": func.__name__,
        "docstring": inspect.getdoc(func) or "",
        "signature": str(inspect.signature(func)),
    }

    # Try to get source file info
    try:
        metadata["source_file"] = inspect.getfile(func)
        source_lines, start_line = inspect.getsourcelines(func)
        metadata["source_line"] = start_line  # int is fine for dict[str, Any]
        # Include first few lines of source for context
        metadata["source_preview"] = "".join(source_lines[:10])
    except (TypeError, OSError):
        # Built-in functions or dynamically created functions may not have source
        pass

    return metadata


async def run_callable_async(
    func: Callable[..., Any],
    timeout: float = 600.0,
    **kwargs: Any,
) -> SubprocessResult:
    """Run async callable with timeout and error handling.

    This function executes an async callable (coroutine function) with the same
    error handling and result format as run_command_async, enabling Python
    functions to be used interchangeably with shell commands in workflows.

    Args:
        func: Async callable to execute (must be async def function)
        timeout: Timeout in seconds (default: 600)
        **kwargs: Optional keyword arguments passed to the callable:
            - working_dir: Current working directory
            - config_dir: Configuration directory
            - env_vars: Environment variables dict
            - state: Workflow state dict

    Returns:
        SubprocessResult with output and status

    Raises:
        TypeError: If func is not an async callable

    Example:
        >>> async def my_setup(working_dir: str = None, **kwargs):
        ...     print("Running setup")
        ...     # Do setup work
        ...     return "Setup complete"
        >>>
        >>> result = await run_callable_async(
        ...     my_setup,
        ...     timeout=300,
        ...     working_dir="/path/to/work"
        ... )
        >>> if result["success"]:
        ...     print(f"Success: {result['output']}")
        >>> else:
        ...     print(f"Failed: {result['stderr']}")
    """
    # Verify func is async callable
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"Callable must be an async function (async def), got {type(func).__name__}"
        )

    start = time.time()

    # Capture stdout to include in output
    captured_stdout = io.StringIO()
    original_stdout = sys.stdout

    try:
        # Redirect stdout to capture print statements
        sys.stdout = captured_stdout

        logger.info(f"Executing callable: {func.__name__}")

        # Execute callable with timeout
        try:
            result = await asyncio.wait_for(func(**kwargs), timeout=timeout)

            duration = time.time() - start

            # Get captured output
            output_lines = []
            stdout_content = captured_stdout.getvalue()
            if stdout_content:
                output_lines.append(stdout_content.rstrip())

            # Include return value if it's a string
            if result is not None and isinstance(result, str):
                output_lines.append(result)

            output = "\n".join(output_lines) if output_lines else ""

            logger.info(f"Callable {func.__name__} completed successfully in {duration:.2f}s")

            return SubprocessResult(
                success=True,
                output=output,
                stderr="",
                exit_code=0,
                duration=duration,
            )

        except TimeoutError:
            duration = time.time() - start
            error_msg = f"Callable {func.__name__} timed out after {timeout} seconds"
            logger.warning(error_msg)

            return SubprocessResult(
                success=False,
                output=captured_stdout.getvalue(),
                stderr=error_msg,
                exit_code=None,
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start

            # Capture full traceback
            tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
            error_output = "".join(tb_lines)

            logger.error(
                f"Callable {func.__name__} failed after {duration:.2f}s: {e}",
                exc_info=True,
            )

            return SubprocessResult(
                success=False,
                output=captured_stdout.getvalue(),
                stderr=error_output,
                exit_code=1,  # Simulate non-zero exit code for failures
                duration=duration,
            )

    finally:
        # Always restore stdout
        sys.stdout = original_stdout
