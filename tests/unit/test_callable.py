"""Unit tests for callable support in Alphanso.

This module contains comprehensive tests for callable functionality across
pre-actions, main scripts, and validators.
"""

import asyncio

import pytest

from alphanso.actions.pre_actions import PreAction
from alphanso.config.schema import (
    MainScriptConfig,
    PreActionConfig,
    ValidatorConfig,
)
from alphanso.graph.nodes import create_validators, run_main_script_node
from alphanso.utils.callable import run_callable_async
from alphanso.validators.callable import CallableValidator


class TestRunCallableAsync:
    """Tests for run_callable_async utility function."""

    @pytest.mark.asyncio
    async def test_successful_callable_execution(self) -> None:
        """Test successful execution of an async callable."""

        async def sample_func(**kwargs) -> str:
            return "Success!"

        result = await run_callable_async(sample_func, timeout=5.0)

        assert result["success"] is True
        assert "Success!" in result["output"]
        assert result["stderr"] == ""
        assert result["exit_code"] == 0
        assert result["duration"] > 0

    @pytest.mark.asyncio
    async def test_callable_with_print_statements(self) -> None:
        """Test callable that prints to stdout."""

        async def printing_func(**kwargs) -> None:
            print("Line 1")
            print("Line 2")

        result = await run_callable_async(printing_func, timeout=5.0)

        assert result["success"] is True
        assert "Line 1" in result["output"]
        assert "Line 2" in result["output"]

    @pytest.mark.asyncio
    async def test_callable_failure_with_exception(self) -> None:
        """Test callable that raises an exception."""

        async def failing_func(**kwargs) -> None:
            raise ValueError("Test error")

        result = await run_callable_async(failing_func, timeout=5.0)

        assert result["success"] is False
        assert "ValueError: Test error" in result["stderr"]
        assert result["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_callable_timeout(self) -> None:
        """Test callable respects timeout."""

        async def slow_func(**kwargs) -> None:
            await asyncio.sleep(10)

        result = await run_callable_async(slow_func, timeout=0.1)

        assert result["success"] is False
        assert "timed out" in result["stderr"]
        assert result["exit_code"] is None

    @pytest.mark.asyncio
    async def test_callable_receives_kwargs(self) -> None:
        """Test callable receives expected kwargs."""

        async def kwargs_func(working_dir=None, env_vars=None, **kwargs) -> str:
            return f"working_dir={working_dir}, env_vars={env_vars}"

        result = await run_callable_async(
            kwargs_func,
            timeout=5.0,
            working_dir="/test/path",
            env_vars={"KEY": "value"},
        )

        assert result["success"] is True
        assert "working_dir=/test/path" in result["output"]
        assert "env_vars={'KEY': 'value'}" in result["output"]

    @pytest.mark.asyncio
    async def test_non_async_callable_raises_error(self) -> None:
        """Test that non-async callables raise TypeError."""

        def sync_func() -> None:  # type: ignore
            pass

        with pytest.raises(TypeError, match="async function"):
            await run_callable_async(sync_func, timeout=5.0)  # type: ignore


class TestPreActionCallable:
    """Tests for PreAction with callable support."""

    @pytest.mark.asyncio
    async def test_preaction_with_callable(self) -> None:
        """Test PreAction executes callable successfully."""

        async def setup_func(**kwargs) -> None:
            print("Setup complete")

        action = PreAction(callable=setup_func, description="Setup")
        result = await action.arun({})

        assert result["success"] is True
        assert result["action"] == "Setup"
        assert "Setup complete" in result["output"]

    @pytest.mark.asyncio
    async def test_preaction_callable_receives_env_vars(self) -> None:
        """Test PreAction passes env_vars to callable."""

        async def env_func(env_vars=None, **kwargs) -> str:
            return f"VAR={env_vars.get('TEST_VAR')}"

        action = PreAction(callable=env_func)
        result = await action.arun({"TEST_VAR": "value123"})

        assert result["success"] is True
        assert "VAR=value123" in result["output"]

    @pytest.mark.asyncio
    async def test_preaction_callable_failure(self) -> None:
        """Test PreAction handles callable failures."""

        async def failing_setup(**kwargs) -> None:
            raise RuntimeError("Setup failed")

        action = PreAction(callable=failing_setup, description="Bad Setup")
        result = await action.arun({})

        assert result["success"] is False
        assert "RuntimeError: Setup failed" in result["stderr"]

    def test_preaction_requires_command_or_callable(self) -> None:
        """Test PreAction requires either command or callable."""
        with pytest.raises(ValueError, match="Either 'command' or 'callable'"):
            PreAction()

    def test_preaction_rejects_both_command_and_callable(self) -> None:
        """Test PreAction rejects both command and callable."""

        async def dummy(**kwargs) -> None:
            pass

        with pytest.raises(ValueError, match="Cannot specify both"):
            PreAction(command="echo test", callable=dummy)


class TestCallableValidator:
    """Tests for CallableValidator class."""

    @pytest.mark.asyncio
    async def test_validator_success(self) -> None:
        """Test validator succeeds when callable returns normally."""

        async def passing_validator(**kwargs) -> None:
            print("Validation passed")

        validator = CallableValidator(
            name="Test Validator", callable=passing_validator, timeout=5.0
        )
        result = await validator.avalidate()

        assert result["success"] is True
        assert result["validator_name"] == "Test Validator"
        assert "Validation passed" in result["output"]

    @pytest.mark.asyncio
    async def test_validator_failure(self) -> None:
        """Test validator fails when callable raises exception."""

        async def failing_validator(**kwargs) -> None:
            raise AssertionError("Validation failed")

        validator = CallableValidator(
            name="Failing Validator", callable=failing_validator, timeout=5.0
        )
        result = await validator.avalidate()

        assert result["success"] is False
        assert result["validator_name"] == "Failing Validator"
        assert "AssertionError: Validation failed" in result["stderr"]


class TestConfigSchema:
    """Tests for config schema with callable support."""

    def test_preaction_config_with_callable(self) -> None:
        """Test PreActionConfig accepts callable."""

        async def setup(**kwargs) -> None:
            pass

        config = PreActionConfig(callable=setup)
        assert config.callable == setup
        assert config.command is None

    def test_preaction_config_validates_mutual_exclusion(self) -> None:
        """Test PreActionConfig validates command/callable mutual exclusion."""

        async def setup(**kwargs) -> None:
            pass

        # Both provided - should fail
        with pytest.raises(ValueError, match="Cannot specify both"):
            PreActionConfig(command="echo test", callable=setup)

        # Neither provided - should fail
        with pytest.raises(ValueError, match="Either 'command' or 'callable'"):
            PreActionConfig()

    def test_mainscript_config_with_callable(self) -> None:
        """Test MainScriptConfig accepts callable."""

        async def main_task(**kwargs) -> None:
            pass

        config = MainScriptConfig(callable=main_task)
        assert config.callable == main_task
        assert config.command is None

    def test_validator_config_with_callable(self) -> None:
        """Test ValidatorConfig accepts callable."""

        async def validate(**kwargs) -> None:
            pass

        config = ValidatorConfig(type="callable", name="Test", callable=validate)
        assert config.callable == validate


class TestValidatorCreation:
    """Tests for create_validators with callable type."""

    def test_creates_callable_validator(self) -> None:
        """Test create_validators handles callable type."""

        async def validator_func(**kwargs) -> None:
            pass

        config = [
            {
                "type": "callable",
                "name": "Custom Validator",
                "callable": validator_func,
                "timeout": 30.0,
            }
        ]

        validators = create_validators(config, working_dir="/test")

        assert len(validators) == 1
        assert isinstance(validators[0], CallableValidator)
        assert validators[0].name == "Custom Validator"
        assert validators[0].timeout == 30.0


class TestMainScriptNode:
    """Tests for run_main_script_node with callable support."""

    @pytest.mark.asyncio
    async def test_main_script_with_callable(self) -> None:
        """Test main script node executes callable."""

        async def main_script(**kwargs) -> str:
            return "Script executed"

        state = {
            "main_script_config": {
                "callable": main_script,
                "description": "Main Task",
                "timeout": 10.0,
            },
            "working_directory": "/test",
            "attempt": 0,
            "max_attempts": 3,
        }

        result = await run_main_script_node(state)

        assert result["main_script_succeeded"] is True
        assert result["main_script_result"]["success"] is True
        assert "Script executed" in result["main_script_result"]["output"]
        assert "callable:" in result["main_script_result"]["command"]

    @pytest.mark.asyncio
    async def test_main_script_callable_failure(self) -> None:
        """Test main script node handles callable failures."""

        async def failing_script(**kwargs) -> None:
            raise Exception("Script failed")

        state = {
            "main_script_config": {
                "callable": failing_script,
                "description": "Failing Task",
                "timeout": 10.0,
            },
            "working_directory": "/test",
            "attempt": 0,
            "max_attempts": 3,
        }

        result = await run_main_script_node(state)

        assert result["main_script_succeeded"] is False
        assert result["main_script_result"]["success"] is False
        assert "Script failed" in result["main_script_result"]["stderr"]
