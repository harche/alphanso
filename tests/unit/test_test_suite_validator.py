"""Unit tests for TestSuiteValidator."""

from unittest.mock import AsyncMock, patch

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

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_successful_test_run(self, mock_run_command: AsyncMock) -> None:
        """Returns success ValidationResult when tests pass."""
        mock_run_command.return_value = {
            "success": True,
            "output": "All tests passed\n",
            "stderr": "",
            "exit_code": 0,
            "duration": 1.5,
        }

        validator = TestSuiteValidator(name="Tests", command="make test")
        result = validator.validate()

        assert result["success"]
        assert result["validator_name"] == "Tests"
        assert result["exit_code"] == 0
        assert "All tests passed" in result["output"]

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_failed_test_run(self, mock_run_command: AsyncMock) -> None:
        """Returns failure ValidationResult when tests fail."""
        mock_run_command.return_value = {
            "success": False,
            "output": "Test output here\nError: test_foo failed\nError: test_bar failed\n",
            "stderr": "",
            "exit_code": 1,
            "duration": 2.0,
        }

        validator = TestSuiteValidator(name="Tests", command="make test")
        result = validator.validate()

        assert not result["success"]
        assert result["exit_code"] == 1
        # Note: With new implementation, stderr is merged into output
        assert "test_foo failed" in result["output"]
        assert "test_bar failed" in result["output"]

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_timeout_handling(self, mock_run_command: AsyncMock) -> None:
        """Returns timeout error when test execution times out."""
        mock_run_command.return_value = {
            "success": False,
            "output": "",
            "stderr": "Command timed out after 600.0 seconds",
            "exit_code": None,
            "duration": 600.0,
        }

        validator = TestSuiteValidator(name="Tests", command="make test", timeout=600.0)
        result = validator.validate()

        assert not result["success"]
        assert result["exit_code"] is None
        assert "timed out" in result["stderr"]
        assert result["metadata"]["timeout"]

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_always_runs_exact_command(self, mock_run_command: AsyncMock) -> None:
        """Verifies that validator runs the exact command specified."""
        mock_run_command.return_value = {
            "success": True,
            "output": "ok\n",
            "stderr": "",
            "exit_code": 0,
            "duration": 0.5,
        }

        validator = TestSuiteValidator(
            name="Tests",
            command="make test",
        )
        validator.validate()

        # Verify run_command_async was called with the exact command
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args
        assert call_args.args[0] == "make test"

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_truncates_stdout_to_last_n_lines(self, mock_run_command: AsyncMock) -> None:
        """Truncates stdout to last N lines."""
        # Create output with 300 lines
        long_output = "\n".join([f"line {i}" for i in range(300)])

        mock_run_command.return_value = {
            "success": True,
            "output": long_output,
            "stderr": "",
            "exit_code": 0,
            "duration": 1.0,
        }

        validator = TestSuiteValidator(name="Tests", command="make test", capture_lines=50)
        result = validator.validate()

        # Should only have last 50 lines
        output_lines = result["output"].strip().split("\n")
        assert len(output_lines) == 50
        assert "line 250" in result["output"]  # Later lines included
        assert "line 0" not in result["output"]  # Early lines excluded

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_includes_full_stderr(self, mock_run_command: AsyncMock) -> None:
        """Includes full stderr regardless of length."""
        long_stderr = "\n".join([f"error {i}" for i in range(300)])

        mock_run_command.return_value = {
            "success": False,
            "output": "",
            "stderr": long_stderr,
            "exit_code": 1,
            "duration": 1.0,
        }

        validator = TestSuiteValidator(name="Tests", command="make test", capture_lines=50)
        result = validator.validate()

        # stderr should be full, not truncated
        assert "error 0" in result["stderr"]
        assert "error 299" in result["stderr"]
        assert result["stderr"].count("\n") == 299

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_working_directory_passed_to_subprocess(self, mock_run_command: AsyncMock) -> None:
        """Passes working_directory to subprocess."""
        mock_run_command.return_value = {
            "success": True,
            "output": "",
            "stderr": "",
            "exit_code": 0,
            "duration": 0.5,
        }

        validator = TestSuiteValidator(
            name="Tests",
            command="make test",
            working_directory="/custom/path",
        )
        validator.validate()

        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.kwargs["working_dir"] == "/custom/path"


class TestAnyCommand:
    """Tests showing TestSuiteValidator works with any command."""

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_go_test_command(self, mock_run_command: AsyncMock) -> None:
        """Works with Go test commands."""
        mock_run_command.return_value = {
            "success": True,
            "output": "PASS\n",
            "stderr": "",
            "exit_code": 0,
            "duration": 0.5,
        }

        validator = TestSuiteValidator(name="Go Tests", command="go test ./...")
        result = validator.validate()

        assert result["success"]
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.args[0] == "go test ./..."

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_pytest_command(self, mock_run_command: AsyncMock) -> None:
        """Works with pytest commands."""
        mock_run_command.return_value = {
            "success": True,
            "output": "===== 10 passed in 2.5s =====\n",
            "stderr": "",
            "exit_code": 0,
            "duration": 2.5,
        }

        validator = TestSuiteValidator(name="Python Tests", command="pytest tests/ -v")
        result = validator.validate()

        assert result["success"]
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.args[0] == "pytest tests/ -v"

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_npm_test_command(self, mock_run_command: AsyncMock) -> None:
        """Works with npm test commands."""
        mock_run_command.return_value = {
            "success": True,
            "output": "Test Suites: 5 passed, 5 total\n",
            "stderr": "",
            "exit_code": 0,
            "duration": 3.0,
        }

        validator = TestSuiteValidator(name="JS Tests", command="npm test")
        result = validator.validate()

        assert result["success"]
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.args[0] == "npm test"

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_make_command(self, mock_run_command: AsyncMock) -> None:
        """Works with make commands."""
        mock_run_command.return_value = {
            "success": True,
            "output": "make[1]: Nothing to be done for 'all'\n",
            "stderr": "",
            "exit_code": 0,
            "duration": 0.2,
        }

        validator = TestSuiteValidator(name="Make Test", command="make all")
        result = validator.validate()

        assert result["success"]
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.args[0] == "make all"

    @patch("alphanso.validators.test_suite.run_command_async")
    def test_bundle_exec_rspec_command(self, mock_run_command: AsyncMock) -> None:
        """Works with bundle exec rspec commands."""
        mock_run_command.return_value = {
            "success": True,
            "output": "20 examples, 0 failures\n",
            "stderr": "",
            "exit_code": 0,
            "duration": 4.0,
        }

        validator = TestSuiteValidator(name="Ruby Tests", command="bundle exec rspec")
        result = validator.validate()

        assert result["success"]
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args.args[0] == "bundle exec rspec"
