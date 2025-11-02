# Alphanso Examples

This directory contains example workflows demonstrating different use cases and features of Alphanso.

## Available Examples

### 🌟 [Hello World](hello-world/)
**Difficulty**: Beginner | **Dependencies**: None

A simple introduction to Alphanso's workflow system. This example uses only basic shell commands and demonstrates:
- Loading YAML configuration
- Running pre-actions sequentially
- Running validators to check conditions
- Variable substitution with `${VAR}` syntax
- LangGraph state machine execution
- Real-time progress display with timing

**Perfect for**: First-time users learning the basics

**Run it using the CLI**:
```bash
uv run alphanso run --config examples/hello-world/config.yaml
```

**Or using the Python API**:
```python
from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig, PreActionConfig

# Create config object
config = ConvergenceConfig(
    name="Hello World",
    max_attempts=10,
    pre_actions=[PreActionConfig(command="echo 'Hello'", description="Greeting")]
)

# Run convergence
result = run_convergence(config=config)
```

---

## Coming Soon

### Kubernetes Rebase (Complex Rebasing)
**Difficulty**: Advanced | **Dependencies**: git, podman, go

Demonstrates rebasing OpenShift's Kubernetes fork with upstream. Shows:
- Complex pre-actions (git merge, container setup)
- Handling merge conflicts
- Vendor updates
- Test suite execution

### Dependency Upgrade
**Difficulty**: Intermediate | **Dependencies**: Language-specific

Automated dependency upgrade workflow showing:
- Breaking change detection
- Iterative fixing
- Test-driven convergence

---

## Running Examples

All examples can be run using the Alphanso CLI:

```bash
# Ensure dependencies are installed
uv sync

# Run any example using the CLI
uv run alphanso run --config examples/<example-name>/config.yaml

# Or use the Python API (example with programmatic config)
python -c "
from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig, PreActionConfig

config = ConvergenceConfig(
    name='Example',
    max_attempts=10,
    pre_actions=[PreActionConfig(command='echo test', description='Test')]
)
result = run_convergence(config=config)
print('Success!' if result['success'] else 'Failed')
"
```

## Creating Your Own Example

Each example should include:
1. `config.yaml` - Alphanso configuration with pre-actions and validators
2. `README.md` - Documentation explaining:
   - What the example demonstrates
   - How to run it using CLI and API
   - Expected output
   - Prerequisites/dependencies
3. `.gitignore` - Ignore generated files (optional)

**Recommended structure**:
```yaml
# config.yaml
name: "Your Example Name"
max_attempts: 10

agent:
  type: "claude-agent-sdk"

pre_actions:
  - command: "your setup command"
    description: "What it does"

validators:
  - type: "command"
    name: "Check Something"
    command: "test -f file.txt"
```

See `hello-world/` for a complete template.
