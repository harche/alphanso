"""Test suite validator - runs any test command and captures output.

This validator runs any command (make test, go test, pytest, npm test, etc.) and
checks the exit code. If it fails, it captures stderr and stdout for the AI agent
to analyze. No framework-specific logic needed - the AI is smart enough to understand
the failures.
"""

import subprocess
from typing import Any

from alphanso.graph.state import ValidationResult
from alphanso.validators.base import Validator


class TestSuiteValidator(Validator):
    """Run any test command and capture output for AI analysis.

    Simply runs the specified command and checks the return code. If non-zero,
    captures stderr and stdout for the AI to analyze. No framework-specific parsing
    needed - the AI can understand test failures from any framework.

    IMPORTANT: This validator ALWAYS runs the exact command you specify. It never
    modifies the command.

    Examples:
        >>> # Go project
        >>> validator = TestSuiteValidator(
        ...     name="Go Tests",
        ...     command="make test"
        ... )

        >>> # Python project
        >>> validator = TestSuiteValidator(
        ...     name="Python Tests",
        ...     command="pytest tests/ -v --cov"
        ... )

        >>> # JavaScript project
        >>> validator = TestSuiteValidator(
        ...     name="JS Tests",
        ...     command="npm test"
        ... )

        >>> # Ruby project
        >>> validator = TestSuiteValidator(
        ...     name="Ruby Tests",
        ...     command="bundle exec rspec"
        ... )
    """

    def __init__(
        self,
        name: str,
        command: str,
        timeout: float = 1800.0,
        capture_lines: int = 200,
        working_directory: str | None = None,
    ):
        """Initialize test suite validator.

        Args:
            name: Name of the validator
            command: Exact command to run (e.g., "make test", "pytest", "npm test")
            timeout: Timeout in seconds (default: 30 minutes)
            capture_lines: Number of output lines to capture (default: 200)
            working_directory: Working directory for command execution
        """
        super().__init__(name, timeout)
        self.command = command
        self.capture_lines = capture_lines
        self.working_directory = working_directory

    def validate(self) -> ValidationResult:
        """Run test command and capture output.

        Returns:
            ValidationResult with full stderr and truncated stdout for AI analysis
        """
        # Run the command as-is
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.working_directory,
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                validator_name=self.name,
                success=False,
                output="",
                stderr=f"Command timed out after {self.timeout}s",
                exit_code=None,
                duration=0.0,
                timestamp=0.0,
                metadata={"timeout": True},
            )

        # Truncate output to last N lines (most relevant errors are usually at the end)
        output = self._truncate_output(result.stdout, self.capture_lines)
        # Always include full stderr (usually contains the important error messages)
        stderr = result.stderr

        return ValidationResult(
            validator_name=self.name,
            success=result.returncode == 0,
            output=output,
            stderr=stderr,
            exit_code=result.returncode,
            duration=0.0,  # Will be set by run()
            timestamp=0.0,  # Will be set by run()
            metadata={},
        )

    def _truncate_output(self, text: str, max_lines: int) -> str:
        """Truncate output to last N lines.

        Args:
            text: Output text to truncate
            max_lines: Maximum number of lines to keep

        Returns:
            Truncated output (last N lines)
        """
        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text

        return "\n".join(lines[-max_lines:])
