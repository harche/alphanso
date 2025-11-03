"""Command validator for running shell commands.

This validator executes shell commands (make, make test, go build, etc.)
and checks their exit codes. It's run by the framework, not by Claude.
"""

import logging
import subprocess

from alphanso.graph.state import ValidationResult
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

    def validate(self) -> ValidationResult:
        """Run command and check exit code.

        Returns:
            ValidationResult with command output and exit status
        """
        logger.debug(f"Running command: {self.command}")
        logger.debug(f"Working directory: {self.working_dir}")
        logger.debug(f"Timeout: {self.timeout}s")

        result = subprocess.run(
            self.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=self.working_dir,
        )

        logger.debug(f"Command exit code: {result.returncode}")

        # Capture last N lines
        stdout_lines = result.stdout.split("\n") if result.stdout else []
        stderr_lines = result.stderr.split("\n") if result.stderr else []

        captured_stdout = "\n".join(stdout_lines[-self.capture_lines :])
        captured_stderr = "\n".join(stderr_lines[-self.capture_lines :])

        return ValidationResult(
            validator_name=self.name,
            success=result.returncode == 0,
            output=captured_stdout,
            stderr=captured_stderr,
            exit_code=result.returncode,
            duration=0.0,  # Will be set by run()
            timestamp=0.0,  # Will be set by run()
            metadata={"command": self.command},
        )
