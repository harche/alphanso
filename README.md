<div align="center">
  <h1>Alphanso</h1>
  <p><strong>AI Assisted Convergence Framework for Automation</strong></p>

  <p>
    <a href="#installation">Installation</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#security">Security</a> •
    <a href="#use-cases">Use Cases</a> •
    <a href="#development">Development</a> •
    <a href="#contributing">Contributing</a>
  </p>
</div>

---

## Overview

Alphanso is a production-grade Python framework that leverages AI convergence loops to automate complex, iterative problem-solving workflows. Built on [LangGraph](https://github.com/langchain-ai/langgraph) state machine orchestration, it enables autonomous resolution of challenging tasks including dependency upgrades, code refactoring, infrastructure updates, and Kubernetes rebasing.

## Workflow Architecture

```
START
  ↓
pre_actions (one-time setup)
  ├─ SUCCESS → run_main_script
  └─ FAILED → END [FAILURE]
  ↓
run_main_script
  ├─ SUCCESS → END [SUCCESS]
  └─ FAILED → ai_fix
               ↓
            validate
               ↓
            decide
               ├─ validators PASSED → increment_attempt → run_main_script (retry)
               ├─ validators FAILED → increment_attempt → ai_fix (loop)
               └─ max attempts → END [FAILURE]
```

The workflow begins with one-time setup operations (pre-actions such as cloning repositories or fetching remotes). Upon successful setup, the main script executes. When failures occur, the AI agent investigates and applies corrective measures. Validators verify environment health before retrying. This cycle continues until the main script succeeds or the maximum attempt threshold is reached.

## Use Cases

Alphanso automates complex, iterative workflows that traditionally require extensive manual intervention:

- **Complex Rebasing & Fork Maintenance**: Rebase forked repositories with upstream changes, handling merge conflicts, dependency updates, and test failures
- **Dependency Upgrades**: Upgrade dependencies across large codebases with automatic break detection and fixing
- **Code Refactoring**: Large-scale refactoring with automated validation and issue resolution
- **Database Migrations**: Execute complex database migrations with automatic conflict resolution
- **Infrastructure Updates**: Update infrastructure configurations with validation and automated fixes
- **Security Patching**: Apply security patches while automatically fixing resulting regressions

## Installation

### From Source

```bash
git clone https://github.com/harche/alphanso.git
cd alphanso
uv sync
```

### Using uv (Recommended)

```bash
uv add git+https://github.com/harche/alphanso.git
```

### Using pip

```bash
pip install git+https://github.com/harche/alphanso.git
```

## Quick Start

### Hello World Example

The following example demonstrates autonomous AI-powered problem resolution with a git merge conflict scenario:

```bash
# Set up authentication (choose one):
# Option 1: Anthropic API
export ANTHROPIC_API_KEY="your-api-key"

# Option 2: Google Vertex AI
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION="your-region"
export ANTHROPIC_VERTEX_PROJECT_ID="your-project-id"
gcloud auth application-default login

# Run the hello world example
uv run alphanso run --config examples/hello-world/config.yaml
```

### Using the CLI

```bash
# Run with a config file
uv run alphanso run --config examples/hello-world/config.yaml

# Pass environment variables
uv run alphanso run --config config.yaml --var K8S_TAG=v1.35.0 --var RELEASE=4.22

# Control logging verbosity (default is INFO - shows all important info)
uv run alphanso run --config config.yaml                 # Default (INFO level)
uv run alphanso run --config config.yaml -v              # DEBUG level (workflow tracking)
uv run alphanso run --config config.yaml -vv             # TRACE level (state dumps)
uv run alphanso run --config config.yaml -q              # Quiet (errors only)

# Write logs to file
uv run alphanso run --config config.yaml --log-file output.log
uv run alphanso run --config config.yaml --log-file logs.json --log-format json
```

### Using the Python API

#### Synchronous Usage

For CLI tools, scripts, and other synchronous contexts:

```python
import logging
from pathlib import Path
from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig

# Load config from YAML file
config = ConvergenceConfig.from_yaml(Path("examples/hello-world/config.yaml"))

# Load system prompt
system_prompt = Path("examples/hello-world/prompts/conflict-resolver.txt").read_text()

# Run convergence
result = run_convergence(
    config=config,
    system_prompt_content=system_prompt,  # Required for AI agent
    env_vars={"CUSTOM_VAR": "value"},     # Optional
    working_directory=".",                 # Optional
    log_level=logging.INFO                 # Optional (default: INFO)
)

# Check results
if result["success"]:
    print("✅ All steps succeeded!")
    for action in result["pre_action_results"]:
        status = "✅" if action["success"] else "❌"
        print(f"{status} {action['action']}")
```

#### Asynchronous Usage

For Kubernetes operators, FastAPI servers, and async applications:

```python
import asyncio
from pathlib import Path
from alphanso.api import arun_convergence
from alphanso.config.schema import ConvergenceConfig

async def main():
    # Load config from YAML file
    config = ConvergenceConfig.from_yaml(Path("examples/hello-world/config.yaml"))

    # Load system prompt
    system_prompt = Path("examples/hello-world/prompts/conflict-resolver.txt").read_text()

    # Run convergence asynchronously
    result = await arun_convergence(
        config=config,
        system_prompt_content=system_prompt,
        env_vars={"CUSTOM_VAR": "value"}
    )

    return result

# Run in event loop
result = asyncio.run(main())

# Or use in async context (e.g., Kubernetes operator with kopf)
# @kopf.on.create('alphanso.io', 'v1', 'convergences')
# async def reconcile(spec, **kwargs):
#     config = ConvergenceConfig(**spec)
#     result = await arun_convergence(config=config, ...)
#     return result
```

### Additional Examples

- **Hello World**: [`examples/hello-world/`](examples/hello-world/) - Git merge conflict resolution with AI agent
- **OpenShift Rebase**: [`examples/openshift-rebase/`](examples/openshift-rebase/) - Complex Kubernetes fork rebasing workflow
- **Dependency Upgrade**: [`examples/dependency-upgrade/`](examples/dependency-upgrade/) - Automated dependency updates

## Security

### Trusted Execution Environment Requirement

**⚠️ IMPORTANT**: Alphanso is designed to run in **trusted, isolated environments only**. The AI agent has unrestricted access to:
- Execute arbitrary shell commands
- Read and modify files in the working directory
- Access environment variables
- Make network requests (git, package managers, etc.)

### Permission Model

Alphanso uses the **bypassPermissions** mode from Claude Agent SDK, which:
- **Grants full file system and command execution access** within the working directory
- **Does NOT require user approval** for each action (designed for automation)
- **Assumes the environment is controlled and secure**

This permission model is appropriate for:
- ✅ CI/CD pipelines running in isolated containers
- ✅ Kubernetes operators in dedicated namespaces
- ✅ Local development environments with disposable directories
- ✅ Sandboxed VMs or containers

This permission model is **NOT appropriate** for:
- ❌ Production systems with sensitive data
- ❌ Shared development environments
- ❌ Systems with access to production credentials
- ❌ Untrusted or multi-tenant environments

### Best Practices

1. **Isolate the Execution Environment**
   ```bash
   # Run in Docker container
   docker run --rm -v $(pwd):/workspace alphanso-image \
     alphanso run --config /workspace/config.yaml

   # Or in dedicated directory
   mkdir /tmp/alphanso-workspace
   cd /tmp/alphanso-workspace
   alphanso run --config config.yaml
   ```

2. **Limit Credentials and Access**
   - Use read-only git credentials when possible
   - Avoid exposing production API keys or secrets
   - Use temporary/scoped credentials for package managers
   - Set restrictive `working_directory` in configuration

3. **Review Configuration Files**
   - Audit `pre_actions` commands for security implications
   - Verify `main_script` doesn't access sensitive systems
   - Check `validators` don't expose confidential data

4. **Monitor and Log**
   - Enable verbose logging to track AI actions: `--log-level DEBUG`
   - Review logs for unexpected behavior
   - Use structured logging for audit trails

5. **Network Isolation**
   - Run in networks with restricted outbound access
   - Use firewall rules to limit external connections
   - Avoid environments with access to internal services

### Threat Model

Alphanso's AI agent:
- **Can execute arbitrary code** provided in prompts or tool calls
- **Has no built-in sandboxing** for command execution
- **Trusts the environment** to provide isolation
- **Does not validate** or sanitize commands before execution

The framework is designed for **automation in controlled environments**, not for untrusted input or adversarial scenarios.

### Reporting Security Issues

If you discover a security vulnerability, please open a [private security advisory on GitHub](https://github.com/harche/alphanso/security/advisories/new). Do not open public issues for security concerns.

## Development

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd alphanso

# Install dependencies including dev tools
uv sync --extra dev
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest -v

# Run with coverage report
uv run pytest -v --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_pre_actions.py -v
```

### Type Checking

```bash
# Run mypy strict type checking
uv run mypy src/alphanso
```

### Code Formatting

```bash
# Format with black
uv run black src/ tests/

# Sort imports with isort
uv run isort src/ tests/

# Lint with ruff
uv run ruff check src/ tests/
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome. Please submit pull requests or open issues for bugs and feature requests.
