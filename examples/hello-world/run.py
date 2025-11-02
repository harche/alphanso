#!/usr/bin/env python3
"""Advanced Hello World example showing LangGraph execution.

This example demonstrates the internal LangGraph workflow by directly
using the graph builder and showing node-by-node execution.
"""

from datetime import datetime
from pathlib import Path

from alphanso.config.schema import ConvergenceConfig
from alphanso.graph.builder import create_convergence_graph
from alphanso.graph.state import ConvergenceState


def main() -> None:
    """Run the hello world example showing LangGraph node execution."""
    # Get configuration
    example_dir = Path(__file__).parent
    config_path = example_dir / "config.yaml"

    print(f"Loading configuration from: {config_path}\n")
    config = ConvergenceConfig.from_yaml(config_path)

    print("=" * 70)
    print(f"Running: {config.name}")
    print("=" * 70)
    print()

    # Create initial state
    env_vars = {"CURRENT_TIME": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    initial_state: ConvergenceState = {
        "pre_actions_completed": False,
        "pre_actions_config": [
            {"command": action.command, "description": action.description}
            for action in config.pre_actions
        ],
        "pre_action_results": [],
        "env_vars": env_vars,
        "attempt": 0,
        "max_attempts": config.max_attempts,
        "success": False,
        "working_directory": str(config_path.parent.absolute()),
    }

    print("🔧 Creating LangGraph state machine...")
    print(f"   Graph structure: START → pre_actions → validate → decide → END")
    print()

    # Create and execute the graph
    graph = create_convergence_graph()

    print("🚀 Executing LangGraph workflow...")
    print("-" * 70)
    print()

    # Execute graph and capture final state
    final_state = graph.invoke(initial_state)

    print("-" * 70)
    print("✅ LangGraph workflow completed!")
    print()

    # Display pre-action results
    print("=" * 70)
    print("Pre-Action Results:")
    print("=" * 70)
    print()

    for action_result in final_state["pre_action_results"]:
        status = "✅ SUCCESS" if action_result["success"] else "❌ FAILED"
        print(f"{status}: {action_result['action']}")

        if action_result["output"]:
            for line in action_result["output"].strip().split("\n"):
                print(f"  │ {line}")

        print()

    # Summary
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print(f"Graph structure: START → pre_actions → validate → decide → END")
    print(f"Pre-actions completed: {final_state['pre_actions_completed']}")
    print(f"Validation status: {'✅ PASSED' if final_state['success'] else '❌ FAILED'}")
    print(f"Working directory: {final_state['working_directory']}")
    print()

    if final_state["success"]:
        print("✅ All steps completed successfully!")
    else:
        print("❌ Some steps failed")
    print()


if __name__ == "__main__":
    main()
