# Hello World Example

This is a simple example demonstrating Alphanso's pre-actions system without any external dependencies.

## What This Example Does

1. **Initializes environment** - Prints a setup message
2. **Creates directories** - Creates an `output/` directory
3. **Writes a greeting** - Creates a file with current date and time using environment variables
4. **Displays the greeting** - Shows the content of the created file

## Running the Example

### Using the Python script:

```bash
# From this directory
uv run python run.py

# Or from the project root
uv run python examples/hello-world/run.py
```

### Using the CLI:

```bash
# From the project root
uv run alphanso run --config examples/hello-world/config.yaml

# Or from this directory
uv run alphanso run --config config.yaml
```

Both approaches show the LangGraph node execution

## Expected Output

```
Loading configuration from: /Users/.../examples/hello-world/config.yaml

======================================================================
NODE: pre_actions
======================================================================
Running pre-actions to set up environment...

[1/5] Initialize environment
     ✅ Success
     │ Step 1: Setting up environment...

[2/5] Create directories
     ✅ Success
     │ Step 2: Creating directories...

[3/5] Create output directory
     ✅ Success

[4/5] Write greeting file
     ✅ Success

[5/5] Display greeting
     ✅ Success
     │ Hello! Current time is 2025-11-02 08:05:35

======================================================================
NODE: validate
======================================================================
Running validators (placeholder - STEP 2 will implement)...
✅ Validation PASSED (all validators will be added in STEP 2)

======================================================================
NODE: decide
======================================================================
Making decision (placeholder - STEP 3 will implement retry logic)...
✅ Decision: END (no retry loop yet)
======================================================================

============================================================
✅ All pre-actions completed successfully!
============================================================
```

**Key Output**: Notice the LangGraph nodes executing in sequence:
- **NODE: pre_actions** - Sets up environment
- **NODE: validate** - Runs validators (placeholder in STEP 1)
- **NODE: decide** - Makes decision (placeholder in STEP 1)

This demonstrates the complete state machine workflow!

## What You'll Learn

This example demonstrates:

- **LangGraph State Machine**: See the complete graph workflow with all nodes executing
- **Graph Structure**: START → pre_actions → validate → decide → END
- **Node Execution**: Watch each node execute in sequence with state updates
- **Configuration Loading**: Loading YAML configuration files
- **Pre-Actions**: Running setup commands before the main convergence loop
- **Variable Substitution**: Using `${CURRENT_TIME}` to inject environment variables dynamically
- **State Management**: How state flows through the graph with partial updates
- **Result Handling**: Checking success/failure of each action

**Key Insights**:
- Uses `create_convergence_graph()` to build the LangGraph state machine
- Nodes print their execution showing the graph flow visually
- Each node (pre_actions, validate, decide) executes and updates state
- Demonstrates placeholder nodes that will be implemented in future steps
- Shows the complete workflow from start to finish with full visibility

## Next Steps

After understanding this example, you can:

1. Modify `config.yaml` to add your own pre-actions
2. Try different shell commands
3. Use more complex variable substitution
4. Explore the other examples in the `examples/` directory

## Files Created

After running this example, you'll find:

```
examples/hello-world/
├── output/
│   └── greeting.txt    # Contains "Hello! Current time is 2025-01-15 14:30:00"
├── config.yaml
├── run.py
└── README.md
```
