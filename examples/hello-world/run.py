#!/usr/bin/env python3
"""Hello World example for Alphanso.

This simple example demonstrates using Alphanso's public API
to run pre-actions without external dependencies.
"""

from pathlib import Path

from alphanso.api import run_convergence


def main() -> None:
    """Run the hello world example using Alphanso API."""
    # Get the directory where this script is located
    example_dir = Path(__file__).parent
    config_path = example_dir / "config.yaml"

    # Run convergence using the API
    print(f"Loading configuration from: {config_path}\n")

    result = run_convergence(
        config_path=config_path,
        # env_vars are optional - CURRENT_TIME is added automatically
        env_vars={},
    )

    # Display header
    print("=" * 60)
    print(f"Running: {result['config_name']}")
    print("=" * 60)
    print()

    print("Executing pre-actions...\n")

    # Display results
    print()
    print("=" * 60)
    print("Results:")
    print("=" * 60)
    print()

    for action_result in result["pre_action_results"]:
        status = "✅ SUCCESS" if action_result["success"] else "❌ FAILED"
        print(f"{status}: {action_result['action']}")

        if action_result["output"]:
            # Indent the output
            for line in action_result["output"].strip().split("\n"):
                print(f"  │ {line}")

        if not action_result["success"] and action_result["stderr"]:
            print(f"  └─ Error: {action_result['stderr']}")

        print()

    # Summary
    print("=" * 60)
    if result["success"]:
        print("✅ All pre-actions completed successfully!")
    else:
        print("❌ Some pre-actions failed")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
