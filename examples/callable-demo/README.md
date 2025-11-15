# Callable Demo

This example demonstrates using Python callables (async functions) instead of shell commands with Alphanso.

## Overview

Traditional Alphanso workflows use YAML configs with shell commands:

```yaml
pre_actions:
  - command: "bash setup.sh"
    description: "Setup"

main_script:
  command: "python process.py"

validators:
  - type: command
    name: "Check"
    command: "pytest"
```

With callable support, you can use Python functions directly:

```python
async def setup(**kwargs):
    print("Setting up...")
    # Python code here

config = ConvergenceConfig(
    pre_actions=[PreActionConfig(callable=setup)],
    main_script=MainScriptConfig(callable=process_data),
    validators=[ValidatorConfig(type="callable", callable=validate)],
)
```

## Benefits of Callables

1. **Type Safety**: Full IDE support and type checking
2. **Python Ecosystem**: Direct access to Python libraries
3. **Better Debugging**: Use Python debugger, not shell scripts
4. **Error Handling**: Pythonic exception handling
5. **No Shell Escaping**: Avoid complex quoting and escaping

## Running the Demo

```bash
cd examples/callable-demo
python demo.py
```

### Example Output

The demo shows a simple workflow with callable pre-actions and main script:

```
======================================================================
CALLABLE DEMO - Using Python Functions with Alphanso
======================================================================

+  0.5s  alphanso.api               INFO      Starting convergence (async): Callable Demo
+  0.5s  alphanso.api               INFO      Working directory: /home/harshal/go/src/github.com/harche/alphanso
+  0.5s  alphanso.api               INFO      Max attempts: 5
+  0.5s  alphanso.api               INFO      Pre-actions: 2
+  0.5s  alphanso.api               INFO      Validators: 0

# Pre-actions execute first
+  0.5s  alphanso.graph.nodes       INFO      [1/2] Setup environment
+  0.5s  alphanso.utils.callable    INFO      Executing callable: setup_environment
+  1.3s  alphanso.utils.callable    INFO      Callable setup_environment completed successfully in 0.80s
+  1.3s  alphanso.graph.nodes       INFO           ✅ Success
+  1.3s  alphanso.graph.nodes       INFO           │ 🔧 Setting up environment in None

+  1.3s  alphanso.graph.nodes       INFO      [2/2] Check dependencies
+  1.3s  alphanso.utils.callable    INFO      Executing callable: check_dependencies
+  1.6s  alphanso.utils.callable    INFO      Callable check_dependencies completed successfully in 0.30s
+  1.6s  alphanso.graph.nodes       INFO           ✅ Success
+  1.6s  alphanso.graph.nodes       INFO           │ 📦 Checking dependencies...

# Main script executes successfully
+  1.6s  alphanso.graph.nodes       INFO      Running main script (attempt 1/5)...
+  1.6s  alphanso.graph.nodes       INFO      Description: Process data
+  1.6s  alphanso.graph.nodes       INFO      Type: Python callable (process_data)
+  1.6s  alphanso.graph.nodes       INFO      Timeout: 30.0s
+  1.6s  alphanso.utils.callable    INFO      Executing callable: process_data
+  2.6s  alphanso.utils.callable    INFO      Callable process_data completed successfully in 1.00s
+  2.6s  alphanso.graph.nodes       INFO      ✅ Main script SUCCEEDED (1.00s)
+  2.6s  alphanso.graph.nodes       INFO         │ 📊 Processing data in /home/harshal/go/src/github.com/harche/alphanso

+  2.6s  alphanso.api               INFO      ✅ Convergence completed successfully - main script succeeded

======================================================================
RESULT
======================================================================
Success: True
Attempts: 0
```

**Note**: This demo focuses on showing how callable metadata (function signature, docstring,
source location) is captured and included in AI prompts when failures occur. The workflow
completes successfully to keep the demo simple and fast.

## How It Works

### Pre-Actions (Callables)

Pre-actions run once before the convergence loop:

```python
async def setup_environment(working_dir: str = None, **kwargs):
    print(f"Setting up in {working_dir}")
    # Setup code here
```

### Main Script (Callable)

The main script is retried until it succeeds:

```python
async def process_data(state: dict = None, **kwargs):
    attempt = state.get('attempt', 0)
    # Main task code here
    if something_wrong:
        raise Exception("Task failed")  # Will retry
    return "Success"
```

### Validators (Callables)

Validators check conditions - exceptions indicate failure:

```python
async def validate_output(**kwargs):
    if not output_valid:
        raise AssertionError("Validation failed")
    # Success - no exception
```

## Function Signatures

All callables receive optional kwargs:

- `working_dir`: Current working directory (str)
- `config_dir`: Configuration directory (str)
- `env_vars`: Environment variables (dict)
- `state`: Workflow state including attempt number (dict)

Functions should be `async def` and accept `**kwargs`:

```python
async def my_function(
    working_dir: str = None,
    state: dict = None,
    **kwargs
):
    # Function implementation
    pass
```

## Error Handling

- **Success**: Function returns normally (or returns a value)
- **Failure**: Function raises an exception
- **Timeout**: Function exceeds timeout limit

Exceptions are treated the same as command failures - they include full tracebacks in stderr.

## Mixing Commands and Callables

You can mix commands and callables in the same config:

```python
config = ConvergenceConfig(
    pre_actions=[
        PreActionConfig(command="git fetch"),  # Shell command
        PreActionConfig(callable=setup_env),   # Python function
    ],
    validators=[
        ValidatorConfig(type="command", name="Build", command="make"),
        ValidatorConfig(type="callable", name="Custom", callable=validate),
    ],
)
```

## Backward Compatibility

All existing YAML configs and command-based workflows continue to work unchanged. Callables are an optional alternative available only through the Python API.
