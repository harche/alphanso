# Custom Workflows Examples

This directory contains examples demonstrating how to use custom workflow topologies in Alphanso.

## Overview

Starting with Phase 1 of the Editable Workflows enhancement, you can now customize the workflow graph topology through configuration. This allows you to:

- Skip unnecessary steps (e.g., validators if you don't need them)
- Change the order of operations
- Create custom retry logic
- Build workflows optimized for your specific use case

## Examples

### 1. Simple Workflow (`simple_workflow.yaml`)

A minimal workflow with just pre-actions and main script, no validators or AI.

**Use case**: Quick tasks that don't need validation or AI intervention.

```yaml
workflow:
  nodes:
    - type: pre_actions
      name: setup
    - type: run_main_script
      name: main_task

  edges:
    - from_node: START
      to_node: setup
    - from_node: setup
      to_node: [main_task, END]
      condition: check_pre_actions
    - from_node: main_task
      to_node: END
```

**Run it:**
```bash
alphanso run examples/custom-workflows/simple_workflow.yaml
```

### 2. Retry Without AI (`retry_without_ai.yaml`)

A workflow that retries the main script without AI intervention, using only validators for health checks.

**Use case**: Flaky tasks that eventually succeed without code changes.

```yaml
workflow:
  nodes:
    - type: pre_actions
      name: setup
    - type: run_main_script
      name: main
    - type: validate
      name: health_check
    - type: decide
      name: decide
    - type: increment_attempt
      name: increment

  edges:
    # ... (see file for full edges)
```

**Run it:**
```bash
alphanso run examples/custom-workflows/retry_without_ai.yaml
```

### 3. Direct AI Fix (`direct_ai_fix.yaml`)

A workflow that goes directly to AI on failure, skipping validators.

**Use case**: Complex failures that need AI investigation immediately.

```yaml
workflow:
  nodes:
    - type: pre_actions
      name: setup
    - type: run_main_script
      name: main
    - type: ai_fix
      name: ai_fix
    - type: increment_attempt
      name: increment

  edges:
    # ... (see file for full edges)
```

**Run it:**
```bash
alphanso run examples/custom-workflows/direct_ai_fix.yaml
```

### 4. Python Demo (`demo.py`)

A Python script demonstrating programmatic creation of custom workflows.

**Run it:**
```bash
python examples/custom-workflows/demo.py
```

**Or:**
```bash
./examples/custom-workflows/demo.py
```

## Built-in Node Types

Phase 1 supports these built-in node types:

| Node Type | Description | When to Use |
|-----------|-------------|-------------|
| `pre_actions` | One-time setup commands | Initialization, workspace setup |
| `run_main_script` | Primary goal to retry | The main task you want to accomplish |
| `validate` | Run health checks | Verify environment health, run tests |
| `ai_fix` | AI agent investigation | Let AI analyze and fix errors |
| `increment_attempt` | Increment loop counter | Track retry attempts |
| `decide` | Pass-through decision node | Route based on validation results |

## Built-in Conditions

These condition functions are available for conditional edges:

| Condition | Description | Returns |
|-----------|-------------|---------|
| `check_pre_actions` | Check if pre-actions succeeded | `continue_to_validate` or `end_pre_action_failure` |
| `check_main_script` | Check if main script succeeded | `end_success` or `continue_to_ai_fix` |
| `should_continue` | Determine next step after validation | `validators_passed`, `end_failure`, or `retry` |

## Workflow Configuration Format

### Nodes

```yaml
workflow:
  nodes:
    - type: <node_type>      # One of: pre_actions, run_main_script, validate, ai_fix, increment_attempt, decide
      name: <unique_name>    # Unique identifier for this node
      config: {}             # Optional node-specific config (reserved for future use)
```

### Edges

```yaml
workflow:
  edges:
    # Unconditional edge
    - from_node: <source>
      to_node: <target>

    # Conditional edge with single target
    - from_node: <source>
      to_node: <target>
      condition: <condition_name>

    # Conditional edge with multiple targets
    - from_node: <source>
      to_node: [<target1>, <target2>, ...]
      condition: <condition_name>
```

### Entry Point

```yaml
workflow:
  entry_point: <node_name>  # Optional, defaults to first node in nodes list
```

## Creating Custom Workflows

### Step 1: Define Nodes

List all nodes you need for your workflow:

```yaml
workflow:
  nodes:
    - type: pre_actions
      name: setup
    - type: run_main_script
      name: execute
    - type: validate
      name: verify
```

### Step 2: Connect Nodes with Edges

Define how nodes connect:

```yaml
workflow:
  edges:
    - from_node: START
      to_node: setup
    - from_node: setup
      to_node: execute
    - from_node: execute
      to_node: verify
    - from_node: verify
      to_node: END
```

### Step 3: Add Conditional Routing

Use conditions for branching logic:

```yaml
workflow:
  edges:
    - from_node: execute
      to_node: [END, verify]      # Multiple targets
      condition: check_main_script # Route based on success/failure
```

### Step 4: Validate and Run

The framework validates your topology:
- All node types must be registered
- Node names must be unique
- Edges must reference valid nodes
- Conditions must be registered
- Graph must be connected

## Programmatic Usage

You can create workflows programmatically in Python:

```python
from alphanso.config.schema import (
    ConvergenceConfig,
    WorkflowConfig,
    NodeConfig,
    EdgeConfig,
    MainScriptConfig,
)

# Define custom workflow
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

# Create config with custom workflow
config = ConvergenceConfig(
    name="my-workflow",
    max_attempts=3,
    main_script=MainScriptConfig(
        command="echo 'Hello'",
        description="Test"
    ),
    workflow=workflow  # Pass custom workflow
)

# Use it
from alphanso.api import run_convergence
result = run_convergence(config)
```

## Backward Compatibility

If you don't specify a `workflow` field in your config, Alphanso uses the default hardcoded topology:

```yaml
name: my-config
max_attempts: 10
# No workflow field - uses default topology
pre_actions: [...]
main_script: {...}
validators: [...]
```

This ensures all existing configs continue to work unchanged.

## Validation Errors

Common validation errors and how to fix them:

### Unknown node type
```
ValueError: Unknown node type: 'my_custom_node'
```
**Fix:** Use one of the built-in node types listed above.

### Duplicate node names
```
ValueError: Duplicate node names found: {'setup'}
```
**Fix:** Ensure each node has a unique `name` field.

### Edge references unknown node
```
ValueError: Edge to 'unknown' references unknown node
```
**Fix:** Make sure all edges reference nodes defined in the `nodes` list (or `START`/`END`).

### Unknown condition
```
ValueError: Unknown condition: 'my_condition'
```
**Fix:** Use one of the built-in conditions listed above.

### Multiple targets without condition
```
ValueError: Edge has multiple targets but no condition
```
**Fix:** Add a `condition` field when using multiple targets in `to_node`.

## Next Steps

1. Try running the examples:
   ```bash
   python examples/custom-workflows/demo.py
   alphanso run examples/custom-workflows/simple_workflow.yaml
   ```

2. Create your own workflow:
   - Start with one of the examples
   - Modify nodes and edges for your use case
   - Test and iterate

3. Read the enhancement plan:
   - See `enhancements/editable-workflows.md` for detailed design
   - Phase 2 will add AI-driven dynamic topology changes

## Questions or Issues?

- Check the main README for general Alphanso documentation
- See `enhancements/editable-workflows.md` for the full design
- Open an issue on GitHub for bugs or feature requests
