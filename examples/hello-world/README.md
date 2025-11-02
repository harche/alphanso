# Hello World Example

This is a simple example demonstrating Alphanso's pre-actions system without any external dependencies.

## What This Example Does

1. **Initializes environment** - Prints a setup message
2. **Creates directories** - Creates an `output/` directory
3. **Writes a greeting** - Creates a file with current date and time using environment variables
4. **Displays the greeting** - Shows the content of the created file

## Running the Example

### Using the CLI (recommended):

```bash
# From the project root
uv run alphanso run --config examples/hello-world/config.yaml

# Or from this directory
uv run alphanso run --config config.yaml
```

### Using the Python script directly:

```bash
# From this directory
uv run python run.py

# Or from the project root
uv run python examples/hello-world/run.py
```

## Expected Output

```
Loading configuration from: .../examples/hello-world/config.yaml

============================================================
Running: Hello World Example
============================================================

Executing pre-actions...

============================================================
Results:
============================================================

✅ SUCCESS: Initialize environment
  │ Step 1: Setting up environment...

✅ SUCCESS: Create directories
  │ Step 2: Creating directories...

✅ SUCCESS: Create output directory

✅ SUCCESS: Write greeting file

✅ SUCCESS: Display greeting
  │ Hello! Current time is 2025-01-15 14:30:00

============================================================
✅ All pre-actions completed successfully!
============================================================
```

## What You'll Learn

This example demonstrates:

- **Configuration Loading**: Loading YAML configuration with `ConvergenceConfig.from_yaml()`
- **State Management**: Creating and passing state through the workflow
- **Pre-Actions**: Running setup commands before the main convergence loop
- **Variable Substitution**: Using `${CURRENT_TIME}` to inject environment variables
- **Result Handling**: Checking success/failure of each action
- **Error Reporting**: Capturing stdout and stderr from commands

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
