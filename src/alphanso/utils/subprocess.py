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
    """Run shell command asynchronously with real-time output streaming.

    This function executes a shell command without blocking the event loop,
    allowing other async tasks to run concurrently. Output is streamed in
    real-time to the logger to provide progress feedback for long-running
    operations.

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
        # Create async subprocess with stdout/stderr captured
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
            cwd=working_dir,
        )

        # Stream output in real-time
        stdout_lines = []

        async def read_stream() -> None:
            """Read and log output in real-time."""
            if process.stdout is None:
                return

            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                if line:  # Only log non-empty lines
                    logger.info(f"  {line}")
                    stdout_lines.append(line)

        # Wait for completion with timeout, while streaming output
        try:
            # Run both the stream reader and wait for process completion
            await asyncio.wait_for(asyncio.gather(read_stream(), process.wait()), timeout=timeout)
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
                output="\n".join(stdout_lines),
                stderr=f"Command timed out after {timeout} seconds",
                exit_code=None,
                duration=duration,
            )

        duration = time.time() - start
        stdout = "\n".join(stdout_lines)

        return SubprocessResult(
            success=process.returncode == 0,
            output=stdout,
            stderr="",  # stderr was merged into stdout
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
