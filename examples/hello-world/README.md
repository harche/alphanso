# Hello World Example

This is a simple example demonstrating Alphanso's pre-actions and validators system without any external dependencies.

## What This Example Does

### Pre-Actions (Setup Phase)
1. **Initializes environment** - Prints a setup message
2. **Creates directories** - Creates an `output/` directory
3. **Writes a greeting** - Creates a file with current date and time using environment variables
4. **Displays the greeting** - Shows the content of the created file

### Validators (Verification Phase)
1. **Check Greeting File Exists** - Verifies the greeting file was created
2. **Verify Greeting Content** - Ensures the file contains "Hello"
3. **Check Directory Structure** - Confirms the output directory exists
4. **Git Conflict Check** - Checks for any Git merge conflicts

## Running the Example

### Using the CLI (Recommended):

```bash
# From the project root
uv run alphanso run --config examples/hello-world/config.yaml

# Or from this directory
cd examples/hello-world
uv run alphanso run --config config.yaml
```

### Using the Python API:

```python
from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig, PreActionConfig, ValidatorConfig

# Create config object (however you want - from YAML, database, hardcoded, etc.)
config = ConvergenceConfig(
    name="Hello World Example",
    max_attempts=10,
    pre_actions=[
        PreActionConfig(command="mkdir -p output", description="Create output directory"),
        PreActionConfig(command="echo 'Hello World' > output/greeting.txt", description="Write greeting")
    ],
    validators=[
        ValidatorConfig(type="command", name="Check File", command="test -f output/greeting.txt")
    ]
)

# Run the convergence workflow
result = run_convergence(config=config)

# Check results
if result["success"]:
    print("✅ All steps succeeded!")
else:
    print("❌ Some steps failed")
```

Both approaches show the complete LangGraph workflow execution

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
Running validators to check current state...

[1/4] Check Greeting File Exists
     ✅ Success (0.01s)

[2/4] Verify Greeting Content
     ✅ Success (0.01s)

[3/4] Check Directory Structure
     ✅ Success (0.01s)

[4/4] Git Conflict Check
     ✅ Success (0.00s)

✅ All validators PASSED

======================================================================
NODE: decide
======================================================================
Making decision (placeholder - STEP 3 will implement retry logic)...
✅ Decision: END (no retry loop yet)
======================================================================

======================================================================
Validation Results:
======================================================================

✅ SUCCESS: Check Greeting File Exists (0.01s)

✅ SUCCESS: Verify Greeting Content (0.01s)

✅ SUCCESS: Check Directory Structure (0.01s)

✅ SUCCESS: Git Conflict Check (0.00s)

======================================================================
Summary:
======================================================================
Graph structure: START → pre_actions → validate → decide → END
Pre-actions completed: True
Validators run: 4
Failed validators: 0
Validation status: ✅ PASSED
Working directory: /Users/.../examples/hello-world

✅ All steps completed successfully!
```

**Key Output**: Notice the LangGraph nodes executing in sequence:
- **NODE: pre_actions** - Sets up environment (5 pre-actions)
- **NODE: validate** - Runs validators (4 validators checking conditions)
- **NODE: decide** - Makes decision (placeholder in STEP 2)

This demonstrates the complete state machine workflow!

## What You'll Learn

This example demonstrates:

- **LangGraph State Machine**: See the complete graph workflow with all nodes executing
- **Graph Structure**: START → pre_actions → validate → decide → END
- **Node Execution**: Watch each node execute in sequence with state updates
- **Configuration Loading**: Loading YAML configuration files
- **Pre-Actions**: Running setup commands before the main convergence loop
- **Validators**: Checking conditions (file existence, content verification, directory structure, Git conflicts)
- **Variable Substitution**: Using `${CURRENT_TIME}` to inject environment variables dynamically
- **State Management**: How state flows through the graph with partial updates
- **Result Handling**: Checking success/failure of each action and validator

**Key Insights**:
- Uses `create_convergence_graph()` to build the LangGraph state machine
- Nodes print their execution showing the graph flow visually
- Each node (pre_actions, validate, decide) executes and updates state
- Validators check conditions WITHOUT fixing them (framework-run checks)
- Shows timing for each validator execution
- Displays detailed results at the end with summary statistics
- Shows the complete workflow from start to finish with full visibility

## Next Steps

After understanding this example, you can:

1. Modify `config.yaml` to add your own pre-actions
2. Add custom validators to check different conditions
3. Try different shell commands (make, test commands, etc.)
4. Use more complex variable substitution
5. Experiment with validator timeout settings
6. Explore the other examples in the `examples/` directory

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
