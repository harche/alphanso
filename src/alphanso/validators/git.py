"""Git conflict validator for checking merge conflicts.

This validator checks for Git merge conflict markers in the working tree.
It's run by the framework, not by Claude.
"""

import asyncio
import logging

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

    async def avalidate(self) -> ValidationResult:
        """Check for git conflict markers asynchronously.

        Async version of validate() for use in async applications.

        Returns:
            ValidationResult indicating whether conflicts were found
        """
        logger.debug("Checking for git conflicts (async) with: git diff --check")
        logger.debug(f"Working directory: {self.working_dir}")

        # git diff --check exits with non-zero if it finds conflict markers
        process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--check",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_dir,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
        except TimeoutError:
            # Kill the process if it times out
            try:
                process.kill()
                await process.wait()
            except Exception as e:
                logger.debug(f"Error killing process: {e}")
            return ValidationResult(
                validator_name=self.name,
                success=False,
                output="",
                stderr=f"Command timed out after {self.timeout} seconds",
                exit_code=None,
                duration=0.0,
                timestamp=0.0,
                metadata={"command": "git diff --check", "has_conflicts": False},
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        has_conflicts = process.returncode != 0
        logger.debug(f"Git conflicts found: {has_conflicts}")

        return ValidationResult(
            validator_name=self.name,
            success=not has_conflicts,
            output=stdout if stdout else "",
            stderr=stderr if stderr else "",
            exit_code=process.returncode,
            duration=0.0,  # Will be set by arun()
            timestamp=0.0,  # Will be set by arun()
            metadata={
                "command": "git diff --check",
                "has_conflicts": has_conflicts,
            },
        )
