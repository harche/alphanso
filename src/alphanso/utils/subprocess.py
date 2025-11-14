"""Async subprocess utilities for running shell commands.

This module provides async wrappers for subprocess execution, allowing
non-blocking command execution in async contexts like Kubernetes operators.
"""

import asyncio
import logging
import time
from typing import TypedDict

logger = logging.getLogger(__name__)


class SubprocessResult(TypedDict):
    """Result from subprocess execution.

    Attributes:
        success: Whether the command succeeded (exit code 0)
        output: Captured stdout
        stderr: Captured stderr
        exit_code: Process exit code (None if exception occurred)
        duration: Time taken to execute in seconds
    """

    success: bool
    output: str
    stderr: str
    exit_code: int | None
    duration: float


async def run_command_async(
    command: str,
    timeout: float = 600.0,
    working_dir: str | None = None,
) -> SubprocessResult:
    """Run shell command asynchronously.

    This function executes a shell command without blocking the event loop,
    allowing other async tasks to run concurrently. Useful for long-running
    operations in async applications (e.g., Kubernetes operators, web servers).

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default: 600)
        working_dir: Working directory for command execution

    Returns:
        SubprocessResult with output and status

    Example:
        >>> result = await run_command_async("make build", timeout=300)
        >>> if result["success"]:
        ...     print("Build succeeded!")
        >>> else:
        ...     print(f"Build failed: {result['stderr']}")
    """
    start = time.time()

    try:
        # Create async subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )

        # Wait for completion with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except TimeoutError:
            # Kill the process if it times out
            try:
                process.kill()
                await process.wait()
            except Exception as e:
                logger.debug(f"Failed to kill timed-out process: {e}")

            duration = time.time() - start
            return SubprocessResult(
                success=False,
                output="",
                stderr=f"Command timed out after {timeout} seconds",
                exit_code=None,
                duration=duration,
            )

        duration = time.time() - start

        # Decode output
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        return SubprocessResult(
            success=process.returncode == 0,
            output=stdout,
            stderr=stderr,
            exit_code=process.returncode,
            duration=duration,
        )

    except Exception as e:
        duration = time.time() - start
        logger.debug(f"Async command execution failed: {e}", exc_info=True)

        return SubprocessResult(
            success=False,
            output="",
            stderr=str(e),
            exit_code=None,
            duration=duration,
        )
