"""Git conflict validator for checking merge conflicts.

This validator checks for Git merge conflict markers in the working tree.
It's run by the framework, not by Claude.
"""

import logging
import subprocess

from alphanso.graph.state import ValidationResult
from alphanso.validators.base import Validator

logger = logging.getLogger(__name__)


class GitConflictValidator(Validator):
    """Validates that there are no Git merge conflicts.

    This validator uses 'git diff --check' to detect conflict markers
    (<<<<<<, >>>>>>, ======) in the working tree.

    The framework runs this validator - it is NOT given to Claude as a tool.

    Attributes:
        name: Validator name
        timeout: Maximum execution time in seconds
        working_dir: Working directory for git command
    """

    def __init__(
        self,
        name: str = "Git Conflict Check",
        timeout: float = 10.0,
        working_dir: str | None = None,
    ) -> None:
        """Initialize git conflict validator.

        Args:
            name: Human-readable validator name (default: "Git Conflict Check")
            timeout: Maximum execution time in seconds (default: 10 seconds)
            working_dir: Working directory for git command (default: None = current dir)
        """
        super().__init__(name, timeout)
        self.working_dir = working_dir

    def validate(self) -> ValidationResult:
        """Check for git conflict markers.

        Returns:
            ValidationResult indicating whether conflicts were found
        """
        logger.debug(f"Checking for git conflicts with: git diff --check")
        logger.debug(f"Working directory: {self.working_dir}")

        # git diff --check exits with non-zero if it finds conflict markers
        result = subprocess.run(
            ["git", "diff", "--check"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=self.working_dir,
        )

        has_conflicts = result.returncode != 0
        logger.debug(f"Git conflicts found: {has_conflicts}")

        return ValidationResult(
            validator_name=self.name,
            success=not has_conflicts,
            output=result.stdout if result.stdout else "",
            stderr=result.stderr if result.stderr else "",
            exit_code=result.returncode,
            duration=0.0,  # Will be set by run()
            timestamp=0.0,  # Will be set by run()
            metadata={
                "command": "git diff --check",
                "has_conflicts": has_conflicts,
            },
        )
