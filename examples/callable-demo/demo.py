#!/usr/bin/env python3
"""Callable Demo - Using Python Functions with Alphanso.

This example demonstrates how to use Python callables (async functions)
instead of shell commands for pre-actions, main scripts, and validators.

Benefits of callables:
- Type safety and IDE support
- Direct access to Python ecosystem
- Better error handling and debugging
- No shell escaping issues
"""

import asyncio
from typing import Any

# Global counters for demo purposes
_process_data_calls = 0
_validate_calls = 0


# Pre-action callables
async def setup_environment(working_dir: str | None = None, **kwargs: Any) -> None:
    """Setup environment before main task.

    This is a pre-action that runs once before the convergence loop.
    """
    print(f"🔧 Setting up environment in {working_dir}")
    print("   - Initializing resources...")
    await asyncio.sleep(0.5)  # Simulate work
    print("   - Loading configuration...")
    await asyncio.sleep(0.3)
    print("✅ Environment setup complete")


async def check_dependencies(**kwargs: Any) -> None:
    """Verify dependencies are available.

    Another pre-action example that validates the environment.
    """
    print("📦 Checking dependencies...")
    required = ["python", "git", "make"]
    for dep in required:
        print(f"   ✓ {dep} available")
        await asyncio.sleep(0.1)


# Main script callables
async def process_data(
    working_dir: str | None = None, state: dict[str, Any] | None = None, **kwargs: Any
) -> str:
    """Main task that processes data.

    This is the main script that gets retried until it succeeds.
    Fails on first call, succeeds on second to demonstrate retry + validators.
    """
    global _process_data_calls
    _process_data_calls += 1

    # Get current attempt from state
    current_attempt = state.get("attempt", 0) + 1 if state else 1
    max_attempts = state.get("max_attempts", 10) if state else 10

    print(f"📊 Processing data in {working_dir}")
    print(f"   Attempt: {current_attempt}/{max_attempts}")

    # Fail on first call, succeed on second
    if current_attempt == 1:
        # Simulate a failure
        print("❌ Data processing failed!")
        raise RuntimeError("Connection timeout while fetching data")
    else:
        print("   - Loading data...")
        await asyncio.sleep(0.5)
        print("   - Transforming records...")
        await asyncio.sleep(0.3)
        print("   - Writing output...")
        await asyncio.sleep(0.2)
        print("✅ Data processing complete!")
        return "Processed 1000 records"


async def simple_task(**kwargs: Any) -> None:
    """A simple task that always succeeds."""
    print("🎯 Running simple task...")
    await asyncio.sleep(0.5)
    print("✅ Task completed successfully")


# Validator callables
async def validate_output(working_dir: str | None = None, **kwargs: Any) -> None:
    """Validate that output meets requirements.

    Validators check conditions. They raise exceptions on failure.
    Always passes for demo purposes.
    """
    print("🔍 Validating output...")
    await asyncio.sleep(0.3)

    # Simulate validation checks - always pass
    checks = [
        "Output file exists",
        "Schema is valid",
        "Data integrity check",
    ]

    for check_name in checks:
        print(f"   ✓ {check_name}")

    print("✅ All validations passed")


async def check_format(working_dir: str | None = None, **kwargs: Any) -> None:
    """Check that data format is correct."""
    print("📋 Checking data format...")
    await asyncio.sleep(0.2)

    # This validator always passes for demo purposes
    print("   ✓ Format is correct")
    print("   ✓ Encoding is UTF-8")
    print("✅ Format check passed")


# Example usage
async def main() -> None:
    """Run the callable demo using Alphanso API."""
    from alphanso.api import arun_convergence
    from alphanso.config.schema import (
        ConvergenceConfig,
        MainScriptConfig,
        PreActionConfig,
        ValidatorConfig,
    )

    print("=" * 70)
    print("CALLABLE DEMO - Using Python Functions with Alphanso")
    print("=" * 70)
    print()

    # Create config using Python callables
    config = ConvergenceConfig(
        name="Callable Demo",
        max_attempts=5,
        working_directory=".",
        # Pre-actions using callables
        pre_actions=[
            PreActionConfig(callable=setup_environment, description="Setup environment"),
            PreActionConfig(callable=check_dependencies, description="Check dependencies"),
        ],
        # Main script using callable
        main_script=MainScriptConfig(
            callable=process_data,  # May fail to demonstrate retry + validators
            description="Process data",
            timeout=30.0,
        ),
        # Validators using callables
        validators=[
            ValidatorConfig(
                type="callable",
                name="Output Validation",
                callable=validate_output,
                timeout=10.0,
            ),
            ValidatorConfig(
                type="callable",
                name="Format Check",
                callable=check_format,
                timeout=10.0,
            ),
        ],
    )

    # Run convergence
    result = await arun_convergence(config=config)

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Success: {result.get('success', False)}")
    print(f"Attempts: {result.get('attempt', 0)}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
