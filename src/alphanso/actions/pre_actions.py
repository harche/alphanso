"""Pre-actions module for executing setup commands before convergence loop.

This module provides the PreAction class for running setup operations
(like git operations, container setup, dependency updates) before entering
the main convergence loop.
"""

import logging
import re
import time
from typing import TypedDict

from alphanso.utils.subprocess import run_command_async

logger = logging.getLogger(__name__)


class PreActionResult(TypedDict):
    """Result from executing a pre-action.

    Attributes:
        action: Description of the action that was run
        success: Whether the action succeeded (exit code 0)
        output: Captured stdout (last 1000 chars)
        stderr: Captured stderr (last 1000 chars)
        exit_code: Process exit code (None if exception occurred)
        duration: Time taken to execute in seconds
    """

    action: str
    success: bool
    output: str
    stderr: str
    exit_code: int | None
    duration: float


class PreAction:
    """Execute pre-actions (setup commands before convergence loop).

    Pre-actions are commands that run once before the main validation/fixing loop.
    Examples include git operations, container setup, dependency updates, etc.

    Failures in pre-actions are captured but don't stop execution - they'll be
    caught in the subsequent validation phase.

    Example:
        >>> action = PreAction(
        ...     command="git fetch upstream",
        ...     description="Fetch upstream changes"
        ... )
        >>> result = action.run({"REPO": "/path/to/repo"})
        >>> if result["success"]:
        ...     print("Fetch successful!")
    """

    def __init__(self, command: str, description: str = "") -> None:
        """Initialize a pre-action.

        Args:
            command: Shell command to execute (supports ${VAR} substitution)
            description: Human-readable description (defaults to command if empty)
        """
        self.command = command
        self.description = description or command

    def run(self, env_vars: dict[str, str], working_dir: str | None = None) -> PreActionResult:
        """Run pre-action with variable substitution (sync wrapper).

        This is a convenience wrapper that calls arun() using asyncio.run().
        The primary implementation is in arun() - this method is automatically
        provided for backward compatibility with sync code.

        Args:
            env_vars: Dictionary of variables for substitution
            working_dir: Optional working directory for command execution.
                        If not provided, uses current process directory.

        Returns:
            PreActionResult with execution details

        Example:
            >>> action = PreAction("git merge upstream/${TAG}")
            >>> result = action.run({"TAG": "v1.35.0"}, working_dir="/path/to/repo")
            >>> # Command executed: "git merge upstream/v1.35.0" in /path/to/repo
        """
        import asyncio

        return asyncio.run(self.arun(env_vars, working_dir))

    async def arun(
        self, env_vars: dict[str, str], working_dir: str | None = None
    ) -> PreActionResult:
        """Run pre-action asynchronously with variable substitution.

        Async version of run() for use in async applications (e.g., Kubernetes operators).
        Variables in the command are substituted using ${VAR_NAME} syntax.
        The command is executed with a 600-second timeout.

        Args:
            env_vars: Dictionary of variables for substitution
            working_dir: Optional working directory for command execution.
                        If not provided, uses current process directory.

        Returns:
            PreActionResult with execution details

        Example:
            >>> action = PreAction("git merge upstream/${TAG}")
            >>> result = await action.arun({"TAG": "v1.35.0"}, working_dir="/path/to/repo")
            >>> # Command executed: "git merge upstream/v1.35.0" in /path/to/repo
        """
        # Substitute variables in command
        expanded_command = self._substitute_vars(self.command, env_vars)

        logger.info(f"Pre-action (async): {self.description}")
        logger.info(f"Command (expanded): {expanded_command}")
        logger.info(f"Working directory: {working_dir}")

        # Run command with timing
        start = time.time()
        try:
            result = await run_command_async(
                expanded_command,
                timeout=600.0,  # 10 minute timeout
                working_dir=working_dir,
            )

            logger.info(f"Pre-action exit code: {result['exit_code']}")

            return PreActionResult(
                action=self.description,
                success=result["success"],
                output=result["output"][-1000:],  # Last 1000 chars
                stderr=result["stderr"][-1000:],
                exit_code=result["exit_code"],
                duration=result["duration"],
            )
        except Exception as e:
            logger.debug(f"Pre-action raised exception: {e}", exc_info=True)
            return PreActionResult(
                action=self.description,
                success=False,
                output="",
                stderr=str(e),
                exit_code=None,
                duration=time.time() - start,
            )

    def _substitute_vars(self, text: str, env_vars: dict[str, str]) -> str:
        """Replace ${VAR} with env_vars['VAR'].

        Supports standard shell variable syntax: ${VARIABLE_NAME}
        Variables not found in env_vars are left unchanged.

        Args:
            text: Text containing ${VAR} placeholders
            env_vars: Dictionary of variable names to values

        Returns:
            Text with variables substituted

        Example:
            >>> self._substitute_vars(
            ...     "echo ${GREETING} ${NAME}",
            ...     {"GREETING": "Hello", "NAME": "World"}
            ... )
            'echo Hello World'
        """
        pattern = r"\$\{(\w+)\}"

        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return env_vars.get(var_name, match.group(0))

        return re.sub(pattern, replacer, text)
