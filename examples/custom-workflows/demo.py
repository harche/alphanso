#!/usr/bin/env python3
"""Demo script for custom workflow topologies.

This script demonstrates how to programmatically create and use custom
workflow topologies with Alphanso.
"""

import asyncio
import logging

from alphanso.config.schema import (
    AgentConfig,
    ConvergenceConfig,
    EdgeConfig,
    MainScriptConfig,
    NodeConfig,
    PreActionConfig,
    ValidatorConfig,
    WorkflowConfig,
)
from alphanso.graph.builder import create_convergence_graph

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def demo_simple_workflow():
    """Demo: Simple workflow without AI or validators."""
    logger.info("=" * 70)
    logger.info("DEMO 1: Simple Workflow (No AI, No Validators)")
    logger.info("=" * 70)

    workflow = WorkflowConfig(
        nodes=[
            NodeConfig(type="pre_actions", name="setup"),
            NodeConfig(type="run_main_script", name="main"),
        ],
        edges=[
            EdgeConfig(from_node="START", to_node="setup"),
            EdgeConfig(
                from_node="setup",
                to_node=["main", "END"],
                condition="check_pre_actions",
            ),
            EdgeConfig(from_node="main", to_node="END"),
        ],
    )

    config = ConvergenceConfig(
        name="simple-workflow-demo",
        max_attempts=1,
        pre_actions=[
            PreActionConfig(
                command="echo 'Setting up...'", description="Setup workspace"
            )
        ],
        main_script=MainScriptConfig(
            command="echo 'Task completed!'", description="Main task"
        ),
        workflow=workflow,
    )

    logger.info(f"Created workflow with {len(workflow.nodes)} nodes:")
    for node in workflow.nodes:
        logger.info(f"  - {node.name} ({node.type})")

    logger.info(f"Graph has {len(workflow.edges)} edges")

    graph = create_convergence_graph(config.workflow)
    logger.info(f"✓ Graph created successfully: {type(graph).__name__}")
    logger.info("")


def demo_custom_retry_loop():
    """Demo: Custom retry loop without AI intervention."""
    logger.info("=" * 70)
    logger.info("DEMO 2: Custom Retry Loop (Validators Only, No AI)")
    logger.info("=" * 70)

    workflow = WorkflowConfig(
        nodes=[
            NodeConfig(type="pre_actions", name="init"),
            NodeConfig(type="run_main_script", name="execute"),
            NodeConfig(type="validate", name="verify"),
            NodeConfig(type="decide", name="decide"),
            NodeConfig(type="increment_attempt", name="increment"),
        ],
        edges=[
            EdgeConfig(from_node="START", to_node="init"),
            EdgeConfig(
                from_node="init",
                to_node=["execute", "END"],
                condition="check_pre_actions",
            ),
            EdgeConfig(
                from_node="execute",
                to_node=["END", "verify"],
                condition="check_main_script",
            ),
            EdgeConfig(from_node="verify", to_node="decide"),
            EdgeConfig(
                from_node="decide",
                to_node=["increment", "END"],
                condition="should_continue",
            ),
            EdgeConfig(from_node="increment", to_node="execute"),
        ],
    )

    config = ConvergenceConfig(
        name="custom-retry-loop",
        max_attempts=5,
        pre_actions=[
            PreActionConfig(command="echo 'Initializing...'", description="Init")
        ],
        main_script=MainScriptConfig(
            command="echo 'Executing task...'", description="Execute task"
        ),
        validators=[
            ValidatorConfig(
                type="command",
                name="health-check",
                command="echo 'System healthy'",
                timeout=10.0,
            )
        ],
        workflow=workflow,
    )

    logger.info("Workflow topology:")
    logger.info("  init -> execute -> verify -> decide -> increment -> execute (loop)")

    graph = create_convergence_graph(config.workflow)
    logger.info(f"✓ Graph created successfully: {type(graph).__name__}")
    logger.info("")


def demo_ai_first_workflow():
    """Demo: Workflow that goes to AI immediately on failure."""
    logger.info("=" * 70)
    logger.info("DEMO 3: AI-First Workflow (Skip Validators)")
    logger.info("=" * 70)

    workflow = WorkflowConfig(
        nodes=[
            NodeConfig(type="pre_actions", name="setup"),
            NodeConfig(type="run_main_script", name="main"),
            NodeConfig(type="ai_fix", name="ai_helper"),
            NodeConfig(type="increment_attempt", name="increment"),
        ],
        edges=[
            EdgeConfig(from_node="START", to_node="setup"),
            EdgeConfig(
                from_node="setup",
                to_node=["main", "END"],
                condition="check_pre_actions",
            ),
            EdgeConfig(
                from_node="main",
                to_node=["END", "ai_helper"],
                condition="check_main_script",
            ),
            EdgeConfig(from_node="ai_helper", to_node="increment"),
            EdgeConfig(from_node="increment", to_node="main"),
        ],
    )

    config = ConvergenceConfig(
        name="ai-first-workflow",
        max_attempts=3,
        pre_actions=[
            PreActionConfig(command="echo 'Setup complete'", description="Setup")
        ],
        main_script=MainScriptConfig(
            command="echo 'Running...'", description="Main script"
        ),
        agent=AgentConfig(),
        workflow=workflow,
    )

    logger.info("Workflow topology:")
    logger.info("  setup -> main -> ai_helper -> increment -> main (loop)")
    logger.info("  (Skips validators, AI sees errors immediately)")

    graph = create_convergence_graph(config.workflow)
    logger.info(f"✓ Graph created successfully: {type(graph).__name__}")
    logger.info("")


def demo_default_topology():
    """Demo: Using default topology (backward compatibility)."""
    logger.info("=" * 70)
    logger.info("DEMO 4: Default Topology (Backward Compatible)")
    logger.info("=" * 70)

    config = ConvergenceConfig(
        name="default-topology-demo",
        max_attempts=10,
        pre_actions=[
            PreActionConfig(command="echo 'Setup'", description="Setup step")
        ],
        main_script=MainScriptConfig(
            command="echo 'Main script'", description="Main script"
        ),
        validators=[
            ValidatorConfig(
                type="command", name="test", command="echo 'Tests pass'"
            )
        ],
        # No workflow specified - uses default
    )

    logger.info("No workflow specified in config")
    logger.info("Using default hardcoded topology")

    graph = create_convergence_graph(config.workflow)
    logger.info(f"✓ Graph created successfully: {type(graph).__name__}")
    logger.info("")


def demo_complex_workflow():
    """Demo: Complex workflow with all node types."""
    logger.info("=" * 70)
    logger.info("DEMO 5: Complex Workflow (All Node Types)")
    logger.info("=" * 70)

    workflow = WorkflowConfig(
        nodes=[
            NodeConfig(type="pre_actions", name="pre"),
            NodeConfig(type="run_main_script", name="main"),
            NodeConfig(type="ai_fix", name="ai"),
            NodeConfig(type="validate", name="validate"),
            NodeConfig(type="decide", name="decide"),
            NodeConfig(type="increment_attempt", name="inc"),
        ],
        edges=[
            EdgeConfig(from_node="START", to_node="pre"),
            EdgeConfig(
                from_node="pre",
                to_node=["main", "END"],
                condition="check_pre_actions",
            ),
            EdgeConfig(
                from_node="main", to_node=["END", "ai"], condition="check_main_script"
            ),
            EdgeConfig(from_node="ai", to_node="validate"),
            EdgeConfig(from_node="validate", to_node="decide"),
            EdgeConfig(
                from_node="decide",
                to_node=["inc", "END"],
                condition="should_continue",
            ),
            EdgeConfig(from_node="inc", to_node="main"),
        ],
        entry_point="pre",
    )

    config = ConvergenceConfig(
        name="complex-workflow",
        max_attempts=10,
        pre_actions=[PreActionConfig(command="echo 'Pre'", description="Pre-action")],
        main_script=MainScriptConfig(command="echo 'Main'", description="Main"),
        validators=[
            ValidatorConfig(type="command", name="v1", command="echo 'Validator 1'"),
            ValidatorConfig(type="command", name="v2", command="echo 'Validator 2'"),
        ],
        agent=AgentConfig(),
        workflow=workflow,
    )

    logger.info(f"Workflow has {len(workflow.nodes)} nodes and {len(workflow.edges)} edges")
    logger.info(f"Entry point: {workflow.entry_point}")
    logger.info("Full convergence loop with all components")

    graph = create_convergence_graph(config.workflow)
    logger.info(f"✓ Graph created successfully: {type(graph).__name__}")
    logger.info("")


def main():
    """Run all demos."""
    logger.info("")
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " " * 15 + "ALPHANSO CUSTOM WORKFLOWS DEMO" + " " * 23 + "║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info("")

    # Run demos
    demo_simple_workflow()
    demo_custom_retry_loop()
    demo_ai_first_workflow()
    demo_default_topology()
    demo_complex_workflow()

    logger.info("=" * 70)
    logger.info("All demos completed successfully! ✓")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Check examples/custom-workflows/*.yaml for YAML examples")
    logger.info("  2. Run: alphanso run examples/custom-workflows/simple_workflow.yaml")
    logger.info("  3. Create your own custom workflows!")
    logger.info("")


if __name__ == "__main__":
    main()
