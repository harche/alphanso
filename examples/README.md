# Alphanso Examples

This directory contains example workflows demonstrating different use cases and features of Alphanso.

## Available Examples

### 🌟 [Hello World](hello-world/)
**Difficulty**: Beginner | **Dependencies**: None

A simple introduction to Alphanso's pre-actions system. This example uses only basic shell commands (mkdir, echo, cat) and demonstrates:
- Loading YAML configuration
- Running pre-actions sequentially
- Variable substitution with `${VAR}` syntax
- Result handling and error reporting

**Perfect for**: First-time users learning the basics

**Run it**:
```bash
uv run python examples/hello-world/run.py
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

All examples can be run from the project root:

```bash
# Ensure dependencies are installed
uv sync

# Run any example
uv run python examples/<example-name>/run.py
```

## Creating Your Own Example

Each example should include:
1. `config.yaml` - Alphanso configuration
2. `run.py` - Python script to execute the workflow
3. `README.md` - Documentation explaining the example
4. `.gitignore` - Ignore generated files

See `hello-world/` for a template.
