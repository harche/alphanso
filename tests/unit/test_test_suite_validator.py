"""Unit tests for TestSuiteValidator."""

from unittest.mock import AsyncMock, Mock, patch

from alphanso.validators.test_suite import TestSuiteValidator


class TestTestSuiteValidatorInit:
    """Tests for TestSuiteValidator initialization."""

    def test_init_with_defaults(self) -> None:
        """Initializes with default parameters."""
        validator = TestSuiteValidator(name="Tests", command="make test")

        assert validator.name == "Tests"
        assert validator.command == "make test"
        assert validator.timeout == 1800.0
        assert validator.capture_lines == 200

    def test_init_with_custom_parameters(self) -> None:
        """Initializes with custom parameters."""
        validator = TestSuiteValidator(
            name="Unit Tests",
            command="pytest tests/",
            timeout=600.0,
            capture_lines=50,
            working_directory="/tmp",
        )

        assert validator.name == "Unit Tests"
        assert validator.command == "pytest tests/"
        assert validator.timeout == 600.0
        assert validator.capture_lines == 50
        assert validator.working_directory == "/tmp"


class TestValidate:
    """Tests for validate method."""

    @patch("asyncio.create_subprocess_shell")
    def test_successful_test_run(self, mock_subprocess: Mock) -> None:
        """Returns success ValidationResult when tests pass."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"All tests passed\n", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(name="Tests", command="make test")
        result = validator.validate()

        assert result["success"]
        assert result["validator_name"] == "Tests"
        assert result["exit_code"] == 0
        assert "All tests passed" in result["output"]

    @patch("asyncio.create_subprocess_shell")
    def test_failed_test_run(self, mock_subprocess: Mock) -> None:
        """Returns failure ValidationResult when tests fail."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                b"Test output here\n",
                b"Error: test_foo failed\nError: test_bar failed\n",
            )
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(name="Tests", command="make test")
        result = validator.validate()

        assert not result["success"]
        assert result["exit_code"] == 1
        assert "test_foo failed" in result["stderr"]
        assert "test_bar failed" in result["stderr"]

    @patch("asyncio.create_subprocess_shell")
    def test_timeout_handling(self, mock_subprocess: Mock) -> None:
        """Returns timeout error when test execution times out."""

        # Create mock process that times out
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=TimeoutError())
        mock_process.kill = Mock()  # kill() is not async in real asyncio
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(name="Tests", command="make test", timeout=600.0)
        result = validator.validate()

        assert not result["success"]
        assert result["exit_code"] is None
        assert "timed out" in result["stderr"]
        assert result["metadata"]["timeout"]

    @patch("asyncio.create_subprocess_shell")
    def test_always_runs_exact_command(self, mock_subprocess: Mock) -> None:
        """Verifies that validator runs the exact command specified."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"ok\n", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(
            name="Tests",
            command="make test",
        )
        validator.validate()

        # Verify subprocess was called with the exact command
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args.args[0] == "make test"

    @patch("asyncio.create_subprocess_shell")
    def test_truncates_stdout_to_last_n_lines(self, mock_subprocess: Mock) -> None:
        """Truncates stdout to last N lines."""
        # Create output with 300 lines
        long_output = "\n".join([f"line {i}" for i in range(300)])

        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(long_output.encode(), b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(
            name="Tests", command="make test", capture_lines=50
        )
        result = validator.validate()

        # Should only have last 50 lines
        output_lines = result["output"].split("\n")
        assert len(output_lines) == 50
        assert "line 250" in result["output"]  # Later lines included
        assert "line 0" not in result["output"]  # Early lines excluded

    @patch("asyncio.create_subprocess_shell")
    def test_includes_full_stderr(self, mock_subprocess: Mock) -> None:
        """Includes full stderr regardless of length."""
        long_stderr = "\n".join([f"error {i}" for i in range(300)])

        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", long_stderr.encode())
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(
            name="Tests", command="make test", capture_lines=50
        )
        result = validator.validate()

        # stderr should be full, not truncated
        assert "error 0" in result["stderr"]
        assert "error 299" in result["stderr"]
        assert result["stderr"].count("\n") == 299

    @patch("asyncio.create_subprocess_shell")
    def test_working_directory_passed_to_subprocess(self, mock_subprocess: Mock) -> None:
        """Passes working_directory to subprocess."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(
            name="Tests",
            command="make test",
            working_directory="/custom/path",
        )
        validator.validate()

        mock_subprocess.assert_called_once()
        assert mock_subprocess.call_args.kwargs["cwd"] == "/custom/path"


class TestAnyCommand:
    """Tests showing TestSuiteValidator works with any command."""

    @patch("asyncio.create_subprocess_shell")
    def test_go_test_command(self, mock_subprocess: Mock) -> None:
        """Works with Go test commands."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"PASS\n", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(name="Go Tests", command="go test ./...")
        result = validator.validate()

        assert result["success"]
        mock_subprocess.assert_called_once()
        assert mock_subprocess.call_args.args[0] == "go test ./..."

    @patch("asyncio.create_subprocess_shell")
    def test_pytest_command(self, mock_subprocess: Mock) -> None:
        """Works with pytest commands."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"passed\n", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(name="Python Tests", command="pytest tests/")
        result = validator.validate()

        assert result["success"]
        assert mock_subprocess.call_args.args[0] == "pytest tests/"

    @patch("asyncio.create_subprocess_shell")
    def test_npm_test_command(self, mock_subprocess: Mock) -> None:
        """Works with npm test commands."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"passed\n", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(name="JS Tests", command="npm test")
        result = validator.validate()

        assert result["success"]
        assert mock_subprocess.call_args.args[0] == "npm test"

    @patch("asyncio.create_subprocess_shell")
    def test_make_command(self, mock_subprocess: Mock) -> None:
        """Works with make commands."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"done\n", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(name="Make Tests", command="make test")
        result = validator.validate()

        assert result["success"]
        assert mock_subprocess.call_args.args[0] == "make test"

    @patch("asyncio.create_subprocess_shell")
    def test_bundle_exec_rspec_command(self, mock_subprocess: Mock) -> None:
        """Works with Ruby rspec commands."""
        # Create mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"passed\n", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        validator = TestSuiteValidator(
            name="Ruby Tests", command="bundle exec rspec"
        )
        result = validator.validate()

        assert result["success"]
        assert mock_subprocess.call_args.args[0] == "bundle exec rspec"
