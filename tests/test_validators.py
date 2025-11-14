"""Unit tests for validators module.

Tests cover:
- Validator base class error handling and timing
- CommandValidator execution and output capture
- GitConflictValidator conflict detection
- create_validators factory function
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from alphanso.graph.nodes import create_validators
from alphanso.graph.state import ValidationResult
from alphanso.validators import CommandValidator, GitConflictValidator, Validator


class TestValidatorBase:
    """Test Validator base class functionality."""

    def test_successful_validation_timing(self) -> None:
        """Test that successful validation captures timing correctly."""

        class SuccessValidator(Validator):
            async def avalidate(self) -> ValidationResult:
                import asyncio

                await asyncio.sleep(0.1)  # Simulate work
                return ValidationResult(
                    validator_name=self.name,
                    success=True,
                    output="All good",
                    stderr="",
                    exit_code=0,
                    duration=0.0,
                    timestamp=0.0,
                    metadata={},
                )

        validator = SuccessValidator("Test Validator", timeout=5.0)
        result = validator.run()

        assert result["success"] is True
        assert result["validator_name"] == "Test Validator"
        assert result["output"] == "All good"
        assert result["duration"] >= 0.1  # Should capture sleep time
        assert result["timestamp"] > 0

    def test_exception_handling(self) -> None:
        """Test that exceptions are caught and converted to failed results."""

        class FailingValidator(Validator):
            async def avalidate(self) -> ValidationResult:
                raise RuntimeError("Something went wrong")

        validator = FailingValidator("Failing Validator", timeout=5.0)
        result = validator.run()

        assert result["success"] is False
        assert result["validator_name"] == "Failing Validator"
        assert "Something went wrong" in result["stderr"]
        assert result["exit_code"] is None
        assert result["duration"] >= 0

    def test_timeout_exception(self) -> None:
        """Test that timeout exceptions are handled correctly."""

        class TimeoutValidator(Validator):
            async def avalidate(self) -> ValidationResult:
                raise TimeoutError()

        validator = TimeoutValidator("Timeout Validator")
        result = validator.run()

        assert result["success"] is False
        # TimeoutError has empty string representation, so just verify it failed
        assert result["exit_code"] is None


class TestCommandValidator:
    """Test CommandValidator functionality."""

    def test_successful_command(self) -> None:
        """Test successful command execution."""
        validator = CommandValidator(
            name="Echo Test",
            command="echo 'Hello World'",
            timeout=5.0,
        )
        result = validator.run()

        assert result["success"] is True
        assert result["validator_name"] == "Echo Test"
        assert "Hello World" in result["output"]
        assert result["exit_code"] == 0
        assert result["stderr"] == ""

    def test_failed_command(self) -> None:
        """Test failed command execution."""
        validator = CommandValidator(
            name="False Test",
            command="exit 1",
            timeout=5.0,
        )
        result = validator.run()

        assert result["success"] is False
        assert result["exit_code"] == 1

    def test_command_with_stderr(self) -> None:
        """Test command that produces stderr output."""
        validator = CommandValidator(
            name="Stderr Test",
            command="echo 'error message' >&2 && exit 1",
            timeout=5.0,
        )
        result = validator.run()

        assert result["success"] is False
        # With streaming, stderr is merged into output
        assert "error message" in result["output"]

    def test_output_line_capture(self) -> None:
        """Test that only last N lines are captured."""
        # Generate 200 lines, but only capture last 50
        command = "for i in $(seq 1 200); do echo $i; done"
        validator = CommandValidator(
            name="Line Capture Test",
            command=command,
            timeout=5.0,
            capture_lines=50,
        )
        result = validator.run()

        assert result["success"] is True
        lines = result["output"].strip().split("\n")
        assert len(lines) <= 51  # 50 + potential empty line
        # Should contain high numbers (151-200)
        assert any(int(line) > 150 for line in lines if line.strip().isdigit())

    def test_working_directory(self, tmp_path) -> None:
        """Test command execution in specific working directory."""
        # Create a test file in tmp directory
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        validator = CommandValidator(
            name="Working Dir Test",
            command="ls test.txt",
            timeout=5.0,
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert "test.txt" in result["output"]

    def test_command_timeout(self) -> None:
        """Test that command timeout is enforced."""
        validator = CommandValidator(
            name="Timeout Test",
            command="sleep 10",
            timeout=0.5,  # Very short timeout
        )

        # Timeout should be handled and result in a failed validation
        result = validator.run()
        assert result["success"] is False
        assert result["exit_code"] is None
        assert "timed out" in result["stderr"].lower()

    def test_metadata_includes_command(self) -> None:
        """Test that metadata includes the command."""
        validator = CommandValidator(
            name="Metadata Test",
            command="echo test",
        )
        result = validator.run()

        assert "command" in result["metadata"]
        assert result["metadata"]["command"] == "echo test"


class TestGitConflictValidator:
    """Test GitConflictValidator functionality."""

    @patch("alphanso.validators.git.run_command_async")
    def test_no_conflicts(self, mock_run_command: AsyncMock) -> None:
        """Test when there are no conflicts."""
        mock_run_command.return_value = {
            "success": True,
            "output": "",
            "stderr": "",
            "exit_code": 0,
            "duration": 0.1,
        }

        validator = GitConflictValidator(
            name="Conflict Test",
            timeout=5.0,
        )
        result = validator.run()

        assert result["success"] is True
        assert result["validator_name"] == "Conflict Test"
        assert result["metadata"]["has_conflicts"] is False
        assert result["metadata"]["command"] == "git diff --check"

    @patch("alphanso.validators.git.run_command_async")
    def test_with_conflicts(self, mock_run_command: AsyncMock) -> None:
        """Test when conflicts are detected."""
        mock_run_command.return_value = {
            "success": False,
            "output": "file.txt:10: leftover conflict marker",
            "stderr": "",
            "exit_code": 1,
            "duration": 0.1,
        }

        validator = GitConflictValidator()
        result = validator.run()

        assert result["success"] is False
        assert result["metadata"]["has_conflicts"] is True
        # With streaming, output is merged
        assert "conflict marker" in result["output"]

    @patch("alphanso.validators.git.run_command_async")
    def test_working_directory(self, mock_run_command: AsyncMock) -> None:
        """Test that working directory is passed to subprocess."""
        mock_run_command.return_value = {
            "success": True,
            "output": "",
            "stderr": "",
            "exit_code": 0,
            "duration": 0.1,
        }

        validator = GitConflictValidator(
            working_dir="/path/to/repo",
        )
        validator.run()

        # Check that run_command_async was called with correct working_dir
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.kwargs["working_dir"] == "/path/to/repo"

    @patch("alphanso.validators.git.run_command_async")
    def test_timeout_parameter(self, mock_run_command: AsyncMock) -> None:
        """Test that timeout is passed through."""
        mock_run_command.return_value = {
            "success": True,
            "output": "",
            "stderr": "",
            "exit_code": 0,
            "duration": 0.1,
        }

        validator = GitConflictValidator(timeout=15.0)
        validator.run()

        # The timeout is passed to run_command_async
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.kwargs["timeout"] == 15.0

    @patch("asyncio.create_subprocess_exec")
    def test_default_name(self, mock_subprocess: Mock) -> None:
        """Test that default name is used when not provided."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = GitConflictValidator()
        result = validator.run()

        assert result["validator_name"] == "Git Conflict Check"


class TestCreateValidators:
    """Test create_validators factory function."""

    def test_create_command_validator(self) -> None:
        """Test creating a command validator."""
        config = [
            {
                "type": "command",
                "name": "Build",
                "command": "make",
                "timeout": 300.0,
                "capture_lines": 50,
            }
        ]

        validators = create_validators(config, working_dir="/path/to/repo")

        assert len(validators) == 1
        assert isinstance(validators[0], CommandValidator)
        assert validators[0].name == "Build"
        assert validators[0].command == "make"
        assert validators[0].timeout == 300.0
        assert validators[0].capture_lines == 50
        assert validators[0].working_dir == "/path/to/repo"

    def test_create_git_conflict_validator(self) -> None:
        """Test creating a git conflict validator."""
        config = [
            {
                "type": "git-conflict",
                "name": "Conflict Check",
                "timeout": 10.0,
            }
        ]

        validators = create_validators(config, working_dir="/path/to/repo")

        assert len(validators) == 1
        assert isinstance(validators[0], GitConflictValidator)
        assert validators[0].name == "Conflict Check"
        assert validators[0].timeout == 10.0
        assert validators[0].working_dir == "/path/to/repo"

    def test_create_multiple_validators(self) -> None:
        """Test creating multiple validators."""
        config = [
            {"type": "command", "name": "Build", "command": "make"},
            {"type": "command", "name": "Test", "command": "make test"},
            {"type": "git-conflict", "name": "Conflicts"},
        ]

        validators = create_validators(config)

        assert len(validators) == 3
        assert isinstance(validators[0], CommandValidator)
        assert isinstance(validators[1], CommandValidator)
        assert isinstance(validators[2], GitConflictValidator)

    def test_empty_config(self) -> None:
        """Test creating validators from empty config."""
        validators = create_validators([])
        assert len(validators) == 0

    def test_unknown_validator_type(self) -> None:
        """Test that unknown validator type raises error."""
        config = [{"type": "unknown", "name": "Invalid"}]

        with pytest.raises(ValueError, match="Unknown validator type: unknown"):
            create_validators(config)

    def test_default_values(self) -> None:
        """Test that default values are used when not provided."""
        config = [
            {
                "type": "command",
                "command": "make",
            }
        ]

        validators = create_validators(config)

        assert len(validators) == 1
        validator = validators[0]
        assert validator.name == "Unknown Command"  # Default name
        assert validator.timeout == 600.0  # Default timeout
        assert validator.capture_lines == 100  # Default capture_lines

    def test_git_conflict_default_name(self) -> None:
        """Test that git-conflict uses default name."""
        config = [{"type": "git-conflict"}]

        validators = create_validators(config)

        assert len(validators) == 1
        assert validators[0].name == "Git Conflict Check"
