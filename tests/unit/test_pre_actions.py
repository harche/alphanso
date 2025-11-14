"""Unit tests for pre-actions module.

This module contains comprehensive tests for the PreAction class and
pre_actions_node function, covering all success criteria from STEP 0.
"""

from unittest.mock import Mock, patch

import pytest

from alphanso.actions.pre_actions import PreAction
from alphanso.graph.nodes import pre_actions_node
from alphanso.graph.state import ConvergenceState


class TestPreAction:
    """Tests for PreAction class."""

    def test_run_command_successfully(self) -> None:
        """Test 1: PreAction runs command successfully."""
        action = PreAction(command="echo 'Hello World'", description="Echo test")

        result = action.run({})

        assert result["success"] is True
        assert result["action"] == "Echo test"
        assert "Hello World" in result["output"]
        assert result["exit_code"] == 0
        assert result["duration"] > 0

    def test_substitutes_variables_correctly(self) -> None:
        """Test 2: PreAction substitutes variables correctly."""
        action = PreAction(
            command="echo ${GREETING} ${NAME}",
            description="Greeting test",
        )

        result = action.run({"GREETING": "Hello", "NAME": "World"})

        assert result["success"] is True
        assert "Hello World" in result["output"]

    def test_handles_command_failures(self) -> None:
        """Test 3: PreAction handles command failures gracefully."""
        action = PreAction(command="exit 1", description="Failing command")

        result = action.run({})

        assert result["success"] is False
        assert result["exit_code"] == 1
        assert result["action"] == "Failing command"
        assert isinstance(result["duration"], float)

    @patch("asyncio.create_subprocess_shell")
    def test_respects_timeout(self, mock_subprocess: Mock) -> None:
        """Test 4: PreAction respects timeout (600s)."""
        from unittest.mock import AsyncMock

        # Create mock process with stdout that triggers timeout
        mock_process = AsyncMock()
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=TimeoutError())
        mock_process.stdout = mock_stdout
        mock_process.kill = Mock()  # kill() is not a coroutine in real asyncio
        mock_process.wait = AsyncMock()

        # Mock create_subprocess_shell to return our mock process
        mock_subprocess.return_value = mock_process

        action = PreAction(command="sleep 1000", description="Timeout test")
        result = action.run({})

        assert result["success"] is False
        assert result["exit_code"] is None
        assert "timed out" in result["stderr"].lower()

    def test_variable_substitution_with_multiple_vars(self) -> None:
        """Test 8: Variable substitution works with multiple vars."""
        action = PreAction(command="echo ${VAR1} ${VAR2} ${VAR3}")

        result = action.run(
            {
                "VAR1": "first",
                "VAR2": "second",
                "VAR3": "third",
            }
        )

        assert result["success"] is True
        assert "first" in result["output"]
        assert "second" in result["output"]
        assert "third" in result["output"]

    def test_variable_substitution_leaves_unknown_vars_unchanged(self) -> None:
        """Test variable substitution with missing variables leaves them as-is."""
        action = PreAction(command="echo '${KNOWN}' '${UNKNOWN}'")

        result = action.run({"KNOWN": "value"})

        assert result["success"] is True
        assert "value" in result["output"]
        # When variable is not found, it should remain as ${UNKNOWN}
        assert "${UNKNOWN}" in result["output"]

    def test_output_truncation(self) -> None:
        """Test that output is truncated to last 1000 chars."""
        # Generate more than 1000 characters of output
        long_text = "a" * 2000
        action = PreAction(command=f"echo '{long_text}'")

        result = action.run({})

        assert result["success"] is True
        assert len(result["output"]) <= 1000

    def test_default_description(self) -> None:
        """Test that description defaults to command if not provided."""
        action = PreAction(command="echo test")

        result = action.run({})

        assert result["action"] == "echo test"

    def test_exception_handling(self) -> None:
        """Test handling of unexpected exceptions."""
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # Mock create_subprocess_shell to raise RuntimeError
            mock_subprocess.side_effect = RuntimeError("Unexpected error")

            action = PreAction(command="test", description="Error test")
            result = action.run({})

            assert result["success"] is False
            assert result["exit_code"] is None
            assert "Unexpected error" in result["stderr"]

    def test_working_directory_parameter(self) -> None:
        """Test PreAction respects working_dir parameter."""
        import tempfile
        from pathlib import Path

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a pre-action that writes to a file
            pre_action = PreAction(
                command="echo 'test' > test_file.txt",
                description="Create test file",
            )

            # Run in the temp directory
            result = pre_action.run({}, working_dir=temp_dir)

            # Should succeed
            assert result["success"] is True

            # File should exist in temp_dir, not current directory
            test_file = Path(temp_dir) / "test_file.txt"
            assert test_file.exists()
            assert test_file.read_text().strip() == "test"

    def test_working_directory_with_relative_paths(self) -> None:
        """Test PreAction with relative paths in working_dir."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create subdirectory
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()

            # Create file in subdirectory
            pre_action = PreAction(
                command="mkdir -p output && echo 'hello' > output/file.txt",
                description="Create nested structure",
            )

            result = pre_action.run({}, working_dir=str(subdir))

            assert result["success"] is True
            output_file = subdir / "output" / "file.txt"
            assert output_file.exists()
            assert output_file.read_text().strip() == "hello"


class TestPreActionsNode:
    """Tests for pre_actions_node function."""

    @pytest.mark.asyncio
    async def test_pre_actions_run_in_config_directory_when_provided(self) -> None:
        """Test that pre-actions run in config_directory when provided (CLI usage)."""
        import os
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to different directory (simulating running from elsewhere)
            original_cwd = os.getcwd()
            try:
                # Simulate running from a different location
                other_dir = Path(temp_dir) / "other"
                other_dir.mkdir()
                os.chdir(other_dir)

                # Config directory is where config.yaml would be
                config_dir = Path(temp_dir) / "config_location"
                config_dir.mkdir()

                state: ConvergenceState = {
                    "pre_actions_completed": False,
                    "pre_actions_config": [
                        # This pre-action creates the working directory
                        {"command": "mkdir -p my_workspace", "description": "Create workspace"},
                        # This verifies we're in config_dir, not current dir or working_directory
                        {"command": "pwd", "description": "Show current dir"},
                    ],
                    "pre_action_results": [],
                    "env_vars": {},
                    "working_directory": str(config_dir / "my_workspace"),
                    "config_directory": str(config_dir),  # Pre-actions run here!
                }

                updated_state = await pre_actions_node(state)

                # Pre-actions should succeed
                assert updated_state["pre_actions_completed"] is True
                assert len(updated_state["pre_action_results"]) == 2
                assert all(r["success"] for r in updated_state["pre_action_results"])

                # Verify workspace was created in config_directory, not current directory
                workspace_in_config = config_dir / "my_workspace"
                workspace_in_current = other_dir / "my_workspace"
                assert (
                    workspace_in_config.exists()
                ), "Pre-action should create working_directory in config_directory"
                assert (
                    not workspace_in_current.exists()
                ), "Pre-action should NOT create in current directory"

                # Verify pwd showed config_directory
                pwd_output = updated_state["pre_action_results"][1]["output"].strip()
                # Resolve both paths to handle symlinks (macOS: /var -> /private/var, Linux: /tmp symlinks)
                pwd_path = Path(pwd_output).resolve()
                config_path = config_dir.resolve()
                assert pwd_path == config_path, (
                    f"Pre-action should run in config_directory.\n"
                    f"Expected: {config_path}\n"
                    f"Got:      {pwd_path}"
                )

            finally:
                os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_pre_actions_run_in_current_directory_when_no_config_directory(self) -> None:
        """Test that pre-actions run in current directory when config_directory is None (API usage)."""
        import os
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                state: ConvergenceState = {
                    "pre_actions_completed": False,
                    "pre_actions_config": [
                        # This pre-action creates the working directory
                        {"command": "mkdir -p my_workspace", "description": "Create workspace"},
                        # This verifies we're in current directory
                        {"command": "pwd", "description": "Show current dir"},
                    ],
                    "pre_action_results": [],
                    "env_vars": {},
                    "working_directory": "my_workspace",
                    "config_directory": None,  # No config directory = use current
                }

                updated_state = await pre_actions_node(state)

                # Pre-actions should succeed
                assert updated_state["pre_actions_completed"] is True
                assert len(updated_state["pre_action_results"]) == 2
                assert all(r["success"] for r in updated_state["pre_action_results"])

                # Verify workspace was created in current directory
                workspace = Path(temp_dir) / "my_workspace"
                assert (
                    workspace.exists()
                ), "Pre-action should create working_directory in current dir"
                assert workspace.is_dir()

                # Verify pwd showed current directory (temp_dir)
                pwd_output = updated_state["pre_action_results"][1]["output"].strip()
                # Resolve both paths to handle symlinks (macOS: /var -> /private/var, Linux: /tmp symlinks)
                pwd_path = Path(pwd_output).resolve()
                temp_path = Path(temp_dir).resolve()
                assert pwd_path == temp_path, (
                    f"Pre-action should run in current dir when config_directory is None.\n"
                    f"Expected: {temp_path}\n"
                    f"Got:      {pwd_path}"
                )

            finally:
                os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_runs_all_actions_sequentially(self) -> None:
        """Test 5: Pre-actions node runs all actions sequentially."""
        state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'first'", "description": "First action"},
                {"command": "echo 'second'", "description": "Second action"},
                {"command": "echo 'third'", "description": "Third action"},
            ],
            "pre_action_results": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        updated_state = await pre_actions_node(state)

        assert updated_state["pre_actions_completed"] is True
        assert len(updated_state["pre_action_results"]) == 3
        assert all(r["success"] for r in updated_state["pre_action_results"])

    @pytest.mark.asyncio
    async def test_continues_on_failures(self) -> None:
        """Test 6: Pre-actions node continues on failures."""
        state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'first'", "description": "First"},
                {"command": "exit 1", "description": "Failing"},
                {"command": "echo 'third'", "description": "Third"},
            ],
            "pre_action_results": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        updated_state = await pre_actions_node(state)

        results = updated_state["pre_action_results"]
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True

    @pytest.mark.asyncio
    async def test_runs_only_once_idempotent(self) -> None:
        """Test 7: Pre-actions node runs only once (idempotent)."""
        state: ConvergenceState = {
            "pre_actions_completed": True,  # Already completed
            "pre_actions_config": [
                {"command": "echo 'test'", "description": "Test"},
            ],
            "pre_action_results": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        updated_state = await pre_actions_node(state)

        # Should return empty dict (no updates)
        assert updated_state == {}

    @pytest.mark.asyncio
    async def test_pre_action_results_captured_in_state(self) -> None:
        """Test 9: Pre-action results are captured in state correctly."""
        state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo 'success'", "description": "Success test"},
            ],
            "pre_action_results": [],
            "env_vars": {},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        updated_state = await pre_actions_node(state)

        results = updated_state["pre_action_results"]
        assert len(results) == 1
        assert results[0]["action"] == "Success test"
        assert results[0]["success"] is True
        assert "success" in results[0]["output"]
        assert "duration" in results[0]
        assert "exit_code" in results[0]

    @pytest.mark.asyncio
    async def test_env_vars_are_substituted(self) -> None:
        """Test that environment variables from state are used."""
        state: ConvergenceState = {
            "pre_actions_completed": False,
            "pre_actions_config": [
                {"command": "echo ${TAG} ${REPO}", "description": "Var test"},
            ],
            "pre_action_results": [],
            "env_vars": {"TAG": "v1.35.0", "REPO": "/path/to/repo"},
            "attempt": 0,
            "max_attempts": 10,
            "success": False,
            "working_directory": ".",
        }

        updated_state = await pre_actions_node(state)

        output = updated_state["pre_action_results"][0]["output"]
        assert "v1.35.0" in output
        assert "/path/to/repo" in output
