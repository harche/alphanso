"""Integration tests for CommandValidator using real commands.

These tests use actual shell commands to verify the validator works
correctly in real-world scenarios.
"""

from pathlib import Path

from alphanso.validators import CommandValidator


class TestCommandValidatorIntegration:
    """Integration tests for CommandValidator with real commands."""

    def test_simple_echo_command(self) -> None:
        """Test basic echo command."""
        validator = CommandValidator(
            name="Echo Test",
            command="echo 'Hello World'",
        )
        result = validator.run()

        assert result["success"] is True
        assert "Hello World" in result["output"]
        assert result["exit_code"] == 0

    def test_ls_command(self, tmp_path: Path) -> None:
        """Test ls command in temporary directory."""
        # Create test files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()

        validator = CommandValidator(
            name="List Files",
            command="ls *.txt",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert "file1.txt" in result["output"]
        assert "file2.txt" in result["output"]

    def test_failed_command_with_error_message(self) -> None:
        """Test command that fails with error message."""
        validator = CommandValidator(
            name="Nonexistent Command",
            command="ls /nonexistent/directory",
        )
        result = validator.run()

        assert result["success"] is False
        assert result["exit_code"] != 0
        # With streaming, stderr is merged into output
        assert "No such file or directory" in result["output"]

    def test_python_script_execution(self, tmp_path: Path) -> None:
        """Test executing a Python script."""
        # Create a simple Python script
        script = tmp_path / "test.py"
        script.write_text("print('Script output')\nprint('Line 2')")

        validator = CommandValidator(
            name="Run Python",
            command=f"python {script}",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert "Script output" in result["output"]
        assert "Line 2" in result["output"]

    def test_grep_command(self, tmp_path: Path) -> None:
        """Test grep command for searching files."""
        # Create file with content
        test_file = tmp_path / "sample.txt"
        test_file.write_text("Line 1\nHello World\nLine 3")

        validator = CommandValidator(
            name="Grep Test",
            command="grep 'Hello' sample.txt",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert "Hello World" in result["output"]

    def test_grep_not_found(self, tmp_path: Path) -> None:
        """Test grep when pattern is not found (non-zero exit)."""
        test_file = tmp_path / "sample.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3")

        validator = CommandValidator(
            name="Grep Not Found",
            command="grep 'NotThere' sample.txt",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        # grep returns 1 when pattern not found
        assert result["success"] is False
        assert result["exit_code"] == 1

    def test_multiline_output_capture(self) -> None:
        """Test capturing multiple lines of output."""
        command = """
        echo 'Line 1'
        echo 'Line 2'
        echo 'Line 3'
        """
        validator = CommandValidator(
            name="Multiline Test",
            command=command,
        )
        result = validator.run()

        assert result["success"] is True
        assert "Line 1" in result["output"]
        assert "Line 2" in result["output"]
        assert "Line 3" in result["output"]

    def test_environment_variables(self, tmp_path: Path) -> None:
        """Test command using environment variables."""
        validator = CommandValidator(
            name="Env Var Test",
            command="echo $HOME",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        # Should output the HOME directory
        assert len(result["output"].strip()) > 0

    def test_piped_commands(self) -> None:
        """Test commands with pipes."""
        validator = CommandValidator(
            name="Pipe Test",
            command="echo 'apple\nbanana\ncherry' | grep 'banana'",
        )
        result = validator.run()

        assert result["success"] is True
        assert "banana" in result["output"]

    def test_command_with_redirection(self, tmp_path: Path) -> None:
        """Test command with output redirection."""
        output_file = tmp_path / "output.txt"

        validator = CommandValidator(
            name="Redirect Test",
            command=f"echo 'test content' > {output_file}",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert output_file.exists()
        assert output_file.read_text().strip() == "test content"

    def test_cd_and_pwd(self, tmp_path: Path) -> None:
        """Test cd and pwd commands."""
        validator = CommandValidator(
            name="CD Test",
            command="pwd",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert str(tmp_path) in result["output"]

    def test_make_command_simulation(self, tmp_path: Path) -> None:
        """Test simulating make command."""
        # Create a simple Makefile
        makefile = tmp_path / "Makefile"
        makefile.write_text(
            """
test:
\techo "Running tests..."
\techo "All tests passed"
"""
        )

        validator = CommandValidator(
            name="Make Test",
            command="make test",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert "Running tests" in result["output"]
        assert "All tests passed" in result["output"]

    def test_exit_code_propagation(self) -> None:
        """Test that exit codes are correctly captured."""
        for exit_code in [0, 1, 2, 127]:
            validator = CommandValidator(
                name=f"Exit {exit_code}",
                command=f"exit {exit_code}",
            )
            result = validator.run()

            assert result["exit_code"] == exit_code
            assert result["success"] == (exit_code == 0)

    def test_large_output_capture(self) -> None:
        """Test capturing large output (tests capture_lines)."""
        # Generate 500 lines, capture last 100
        validator = CommandValidator(
            name="Large Output",
            command="for i in $(seq 1 500); do echo $i; done",
            capture_lines=100,
        )
        result = validator.run()

        assert result["success"] is True
        lines = result["output"].strip().split("\n")
        # Should have around 100 lines (last 100 of 500)
        assert len(lines) <= 101
        # Should contain high numbers (401-500)
        numbers = [int(line) for line in lines if line.strip().isdigit()]
        assert any(n > 400 for n in numbers)
        # Should NOT contain low numbers (1-100)
        assert not any(n <= 100 for n in numbers)

    def test_timeout_with_real_sleep(self) -> None:
        """Test that timeout actually kills long-running commands."""
        validator = CommandValidator(
            name="Timeout Test",
            command="sleep 5",
            timeout=0.5,
        )

        # Should timeout and return a failed result
        result = validator.run()
        assert result["success"] is False
        assert result["exit_code"] is None
        assert "timed out" in result["stderr"].lower()

    def test_stderr_and_stdout_together(self) -> None:
        """Test command that produces both stdout and stderr."""
        command = """
        echo 'stdout message'
        echo 'stderr message' >&2
        """
        validator = CommandValidator(
            name="Mixed Output",
            command=command,
        )
        result = validator.run()

        assert result["success"] is True
        assert "stdout message" in result["output"]
        # With streaming, stderr is merged into output
        assert "stderr message" in result["output"]

    def test_working_directory_affects_relative_paths(self, tmp_path: Path) -> None:
        """Test that working_dir affects relative path resolution."""
        # Create subdirectory with file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test.txt").write_text("content")

        # Command uses relative path
        validator = CommandValidator(
            name="Relative Path Test",
            command="cat test.txt",
            working_dir=str(subdir),
        )
        result = validator.run()

        assert result["success"] is True
        assert "content" in result["output"]

    def test_sequential_commands(self, tmp_path: Path) -> None:
        """Test multiple commands in sequence."""
        validator = CommandValidator(
            name="Sequential Commands",
            command="echo 'first' && echo 'second' && echo 'third'",
            working_dir=str(tmp_path),
        )
        result = validator.run()

        assert result["success"] is True
        assert "first" in result["output"]
        assert "second" in result["output"]
        assert "third" in result["output"]

    def test_failed_sequential_commands(self) -> None:
        """Test that && stops on first failure."""
        validator = CommandValidator(
            name="Sequential Fail",
            command="echo 'first' && exit 1 && echo 'third'",
        )
        result = validator.run()

        assert result["success"] is False
        assert "first" in result["output"]
        # 'third' should NOT appear because exit 1 stops the chain
        assert "third" not in result["output"]
