"""Command validator for running shell commands.

This validator executes shell commands (make, make test, go build, etc.)
and checks their exit codes. It's run by the framework, not by Claude.
"""

import logging

from alphanso.graph.state import ValidationResult
from alphanso.utils.subprocess import run_command_async
from alphanso.validators.base import Validator

logger = logging.getLogger(__name__)


class CommandValidator(Validator):
    """Validates by running a shell command.

    This validator executes commands like 'make', 'make test', 'go build ./...'
    and considers the validation successful if the exit code is 0.

    The framework runs this validator - it is NOT given to Claude as a tool.

    Attributes:
        name: Validator name
        command: Shell command to execute
        timeout: Maximum execution time in seconds
        capture_lines: Number of output lines to capture (from end)
        working_dir: Working directory for command execution
    """

    def __init__(
        self,
        name: str,
        command: str,
        timeout: float = 600.0,
        capture_lines: int = 100,
        working_dir: str | None = None,
    ) -> None:
        """Initialize command validator.

        Args:
            name: Human-readable validator name
            command: Shell command to execute
            timeout: Maximum execution time in seconds (default: 10 minutes)
            capture_lines: Number of output lines to capture from end (default: 100)
            working_dir: Working directory for command execution (default: None = current dir)
        """
        super().__init__(name, timeout)
        self.command = command
        self.capture_lines = capture_lines
        self.working_dir = working_dir

    async def avalidate(self) -> ValidationResult:
        """Run command asynchronously and check exit code.

        Async version of validate() for use in async applications.

        Returns:
            ValidationResult with command output and exit status
        """
        logger.info(f"Running command (async): {self.command}")
        logger.info(f"Working directory: {self.working_dir}")
        logger.info(f"Timeout: {self.timeout}s")

        result = await run_command_async(
            self.command,
            timeout=self.timeout,
            working_dir=self.working_dir,
        )

        logger.info(f"Command exit code: {result['exit_code']}")

        # Capture last N lines
        stdout_lines = result["output"].split("\n") if result["output"] else []
        stderr_lines = result["stderr"].split("\n") if result["stderr"] else []

        captured_stdout = "\n".join(stdout_lines[-self.capture_lines :])
        captured_stderr = "\n".join(stderr_lines[-self.capture_lines :])

        return ValidationResult(
            validator_name=self.name,
            success=result["success"],
            output=captured_stdout,
            stderr=captured_stderr,
            exit_code=result["exit_code"],
            duration=0.0,  # Will be set by arun()
            timestamp=0.0,  # Will be set by arun()
            metadata={"command": self.command},
        )
