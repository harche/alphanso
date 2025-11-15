"""Integration tests for custom workflow execution."""

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


class TestCustomWorkflowExecution:
    """Integration tests for executing custom workflows."""

    def test_simple_success_workflow(self):
        """Test creating a simple workflow graph."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
            ],
            edges=[
                EdgeConfig(from_node="START", to_node="setup"),
                EdgeConfig(from_node="setup", to_node="main"),
                EdgeConfig(from_node="main", to_node="END"),
            ],
        )

        config = ConvergenceConfig(
            name="simple-success-workflow",
            max_attempts=3,
            pre_actions=[PreActionConfig(command="echo 'setup'", description="Setup step")],
            main_script=MainScriptConfig(command="echo 'success'", description="Main script"),
            validators=[],
            agent=AgentConfig(),
            workflow=workflow,
        )

        # Create graph - should not raise
        graph = create_convergence_graph(config.workflow)
        assert graph is not None

    def test_workflow_with_validators(self):
        """Test workflow with validation step."""
        workflow = WorkflowConfig(
            nodes=[
                NodeConfig(type="pre_actions", name="setup"),
                NodeConfig(type="run_main_script", name="main"),
                NodeConfig(type="ai_fix", name="fix"),
                NodeConfig(type="validate", name="check"),
                NodeConfig(type="decide", name="decide"),
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
                    to_node=["END", "fix"],
                    condition="check_main_script",
                ),
                EdgeConfig(from_node="fix", to_node="check"),
                EdgeConfig(from_node="check", to_node="decide"),
                EdgeConfig(
                    from_node="decide",
                    to_node=["increment", "END"],
                    condition="should_continue",
                ),
                EdgeConfig(from_node="increment", to_node="main"),
            ],
        )

        config = ConvergenceConfig(
            name="workflow-with-validators",
            max_attempts=3,
            pre_actions=[PreActionConfig(command="echo 'setup'", description="Setup")],
            main_script=MainScriptConfig(command="echo 'main'", description="Main script"),
            validators=[
                ValidatorConfig(
                    type="command",
                    name="health-check",
                    command="echo 'healthy'",
                    timeout=10.0,
                )
            ],
            agent=AgentConfig(),
            workflow=workflow,
        )

        # Create graph - should not raise
        graph = create_convergence_graph(config.workflow)
        assert graph is not None

    def test_minimal_workflow(self):
        """Test minimal workflow with just main script."""
        workflow = WorkflowConfig(
            nodes=[NodeConfig(type="run_main_script", name="main")],
            edges=[
                EdgeConfig(from_node="START", to_node="main"),
                EdgeConfig(from_node="main", to_node="END"),
            ],
        )

        config = ConvergenceConfig(
            name="minimal-workflow",
            max_attempts=1,
            main_script=MainScriptConfig(command="echo 'done'", description="Just run this"),
            workflow=workflow,
        )

        graph = create_convergence_graph(config.workflow)
        assert graph is not None


class TestWorkflowYAMLParsing:
    """Test parsing workflow configs from YAML-like dictionaries."""

    def test_parse_workflow_from_dict(self):
        """Test creating WorkflowConfig from dictionary."""
        data = {
            "nodes": [
                {"type": "pre_actions", "name": "setup"},
                {"type": "run_main_script", "name": "main"},
            ],
            "edges": [
                {"from_node": "START", "to_node": "setup"},
                {"from_node": "setup", "to_node": "main"},
                {"from_node": "main", "to_node": "END"},
            ],
        }

        workflow = WorkflowConfig(**data)
        assert len(workflow.nodes) == 2
        assert len(workflow.edges) == 3
        assert workflow.nodes[0].type == "pre_actions"
        assert workflow.nodes[0].name == "setup"

    def test_parse_workflow_with_conditional_edges(self):
        """Test parsing workflow with conditional edges from dict."""
        data = {
            "nodes": [
                {"type": "pre_actions", "name": "setup"},
                {"type": "run_main_script", "name": "main"},
            ],
            "edges": [
                {"from_node": "START", "to_node": "setup"},
                {
                    "from_node": "setup",
                    "to_node": ["main", "END"],
                    "condition": "check_pre_actions",
                },
            ],
        }

        workflow = WorkflowConfig(**data)
        conditional_edge = next(e for e in workflow.edges if e.condition)
        assert conditional_edge.condition == "check_pre_actions"
        assert isinstance(conditional_edge.to_node, list)

    def test_parse_complete_config_with_workflow(self):
        """Test parsing complete ConvergenceConfig with workflow."""
        data = {
            "name": "complete-config",
            "max_attempts": 5,
            "pre_actions": [{"command": "echo 'init'", "description": "Init"}],
            "main_script": {
                "command": "python script.py",
                "description": "Run script",
            },
            "validators": [
                {
                    "type": "command",
                    "name": "test",
                    "command": "pytest",
                    "timeout": 300.0,
                }
            ],
            "workflow": {
                "nodes": [
                    {"type": "pre_actions", "name": "setup"},
                    {"type": "run_main_script", "name": "main"},
                ],
                "edges": [
                    {"from_node": "START", "to_node": "setup"},
                    {"from_node": "setup", "to_node": "main"},
                    {"from_node": "main", "to_node": "END"},
                ],
            },
        }

        config = ConvergenceConfig(**data)
        assert config.name == "complete-config"
        assert config.workflow is not None
        assert len(config.workflow.nodes) == 2
        assert len(config.workflow.edges) == 3


class TestDefaultTopologyIntegration:
    """Test that default topology still works when workflow is None."""

    def test_config_without_workflow_uses_default(self):
        """Test that config without workflow field uses default topology."""
        config = ConvergenceConfig(
            name="default-topology-test",
            max_attempts=3,
            pre_actions=[PreActionConfig(command="echo 'setup'", description="Setup")],
            main_script=MainScriptConfig(command="echo 'main'", description="Main script"),
            validators=[
                ValidatorConfig(
                    type="command",
                    name="check",
                    command="echo 'ok'",
                )
            ],
        )

        # workflow should be None
        assert config.workflow is None

        # Should still create graph successfully
        graph = create_convergence_graph(config.workflow)
        assert graph is not None

    def test_config_with_explicit_none_workflow(self):
        """Test config with explicitly set workflow=None."""
        config = ConvergenceConfig(
            name="explicit-none-test",
            max_attempts=3,
            main_script=MainScriptConfig(command="echo 'test'", description="Test"),
            workflow=None,
        )

        assert config.workflow is None
        graph = create_convergence_graph(config.workflow)
        assert graph is not None
