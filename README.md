# Alphanso

> AI-assisted iterative problem resolution framework

Alphanso is a Python framework for automating complex, iterative problem-solving workflows with AI assistance. It enables automated tasks like dependency upgrades, code refactoring, and Kubernetes rebasing through intelligent workflow orchestration.

## 🎯 Use Cases

Alphanso excels at automating complex, iterative workflows that traditionally require manual intervention:

### 🔄 Complex Rebasing & Fork Maintenance
Automatically rebase forked repositories with upstream changes, handling complex merge conflicts, dependency updates, and test failures through intelligent iteration.

**Example**: Rebase OpenShift's Kubernetes fork onto upstream v1.35.0
- Merge upstream tag → resolve conflicts → update vendors → run tests → fix failures → iterate until green

**Other Examples**:
- Enterprise forks of open-source projects
- Customized distributions (RHEL, Ubuntu derivatives)
- Long-lived feature branches with extensive divergence

### 📦 Dependency Upgrades
Upgrade dependencies across large codebases with automatic break detection and fixing.

**Example**: Upgrade from Go 1.20 to 1.21
- Update go.mod → build → identify API changes → fix breaking changes → test → iterate

### 🔨 Code Refactoring
Large-scale refactoring with automated validation and issue resolution.

**Example**: Migrate from deprecated API to new API
- Refactor code → run linter → execute tests → fix issues → iterate until all checks pass

### 🗄️ Database Migrations
Execute complex database migrations with automatic conflict resolution.

**Example**: Schema migration across microservices
- Apply migration → validate schema → resolve conflicts → test data integrity → iterate

### 🏗️ Infrastructure Updates
Update infrastructure configurations with validation and automated fixes.

**Example**: Upgrade Terraform providers
- Update provider versions → plan changes → validate → fix deprecated syntax → apply → iterate

### 🔒 Security Patching
Apply security patches while automatically fixing resulting regressions.

**Example**: Patch critical vulnerability
- Apply patch → build → run security tests → fix regressions → verify → iterate

## 🚀 Key Features

- **Pre-Actions System**: Execute setup commands before entering the convergence loop
- **Validator System**: Check conditions (build, test, conflicts) with timing and detailed results
- **Multiple Agent SDKs**: Support for Claude Agent SDK and OpenAI Agent SDK
- **Variable Substitution**: Dynamic environment variable injection in commands
- **Type-Safe Configuration**: Pydantic-based YAML configuration with validation
- **LangGraph Workflow**: State machine orchestration with visual execution flow

## 📦 Installation

### Using uv (recommended)

```bash
uv add alphanso
```

### Using pip

```bash
pip install alphanso
```

## 🎯 Quick Start

### Hello World Example

The simplest way to get started is with the hello world example that demonstrates **autonomous AI-powered problem resolution**:

```bash
# Clone the repository
git clone <repo-url>
cd alphanso

# Install dependencies (including Claude Agent SDK)
uv sync

# Set up authentication (choose one):
# Option 1: Anthropic API
export ANTHROPIC_API_KEY="your-api-key"

# Option 2: Google Vertex AI
export ANTHROPIC_VERTEX_PROJECT_ID="your-project-id"
gcloud auth application-default login

# Run the hello world example
uv run alphanso run --config examples/hello-world/config.yaml
```

This example demonstrates:
- **LangGraph state machine**: Full convergence loop with retry
- **Pre-actions**: Automatic git repository setup with merge conflict
- **Validators**: Git conflict detection
- **AI Agent Integration**: Claude autonomously investigates and fixes issues
- **Streaming output**: Real-time display of Claude's thinking and tool usage
- **Complete workflow**: From setup to resolution with full transparency


### Configuration Example

Here's what the hello world configuration looks like (`examples/hello-world/config.yaml`):

```yaml
name: "Git Merge Conflict Resolution"
max_attempts: 5

# Working directory for commands and agent
working_directory: "."

# Pre-actions - setup and create merge conflict
pre_actions:
  - command: "bash setup.sh"
    description: "Setup git repositories with conflict"

  - command: "cd git-repos/fork && git fetch upstream"
    description: "Fetch upstream changes"

  - command: "cd git-repos/fork && git merge v2.0.0 || true"
    description: "Attempt merge (will conflict)"

# Validators - check for merge conflicts
validators:
  - type: "command"
    name: "Git Conflict Check"
    command: "cd git-repos/fork && git diff --check"
    timeout: 10

# Agent configuration
agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5@20250929"
    system_prompt_file: "prompts/conflict-resolver.txt"

retry_strategy:
  type: hybrid
```

The system prompt (`prompts/conflict-resolver.txt`) guides Claude:
```
You are a git merge conflict resolution assistant.

IMPORTANT: All git operations and file edits should be done in the git-repos/fork directory.

Your task is to resolve merge conflicts that occur when merging upstream changes
into a forked repository...
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

You can also use Alphanso programmatically. The API accepts `ConvergenceConfig` objects:

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

**For more control over logging**, configure it yourself before calling `run_convergence()`:

```python
import logging
from pathlib import Path
from alphanso.utils.logging import setup_logging
from alphanso.api import run_convergence

# Setup logging with file output
setup_logging(
    level=logging.DEBUG,
    log_file=Path("alphanso.log"),
    log_format="json",  # or "text"
    enable_colors=True
)

# Now run convergence (will use your logging config)
result = run_convergence(config=config, system_prompt_content=system_prompt)
```

The `run_convergence()` function:
- **Takes**:
  - `config`: ConvergenceConfig object
  - `system_prompt_content`: System prompt for AI agent (required)
  - `env_vars`: Optional environment variables
  - `working_directory`: Optional working directory
  - `log_level`: Logging level (default: `logging.INFO`)
- **Returns**: `ConvergenceResult` with:
  - `success`: bool - Overall success status
  - `pre_action_results`: list - Results from each pre-action
  - `config_name`: str - Name from the config
  - `working_directory`: str - Working directory used

### Logging and Diagnostics

Alphanso provides comprehensive logging with Rich console output, structured JSON logging, and configurable verbosity levels.

#### CLI Logging

Control logging output with command-line flags:

```bash
# Default: INFO level (show all important info - validator results, AI actions, context)
uv run alphanso run --config config.yaml

# DEBUG level: Add workflow tracking and state transitions
uv run alphanso run --config config.yaml -v

# TRACE level: Add state dumps and development diagnostics
uv run alphanso run --config config.yaml -vv

# Quiet mode: Errors only
uv run alphanso run --config config.yaml -q

# Write logs to file (text format)
uv run alphanso run --config config.yaml --log-file output.log

# Write logs to file (JSON format for parsing)
uv run alphanso run --config config.yaml --log-file logs.json --log-format json
```

**Log Levels**:
- **ERROR** (`-q`): Only critical errors
- **INFO** (default): All important output - validator results, AI actions, tool usage, context sent to AI
- **DEBUG** (`-v`): Add workflow tracking - node transitions, routing decisions, detailed tool I/O
- **TRACE** (`-vv`): Add state dumps and dev diagnostics - full state at key points, internal details

**Log Formats**:
- **text**: Human-readable colored output (Rich console)
- **json**: Structured logging for machine parsing

#### API Logging

Configure logging programmatically:

```python
import logging
from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig
from alphanso.utils.logging import setup_logging

# Option 1: Configure logging yourself
setup_logging(
    level=logging.DEBUG,
    log_file=Path("alphanso-debug.log"),
    log_format="text",
    enable_colors=True
)

# Option 2: Let run_convergence configure it
result = run_convergence(
    config=config,
    system_prompt_content=system_prompt,
    log_level=logging.DEBUG  # Only used if logging not already configured
)
```

**Logging Features**:
- **Rich Console Output**: Colored, formatted output with emoji icons
- **Hierarchical Loggers**: All loggers under `alphanso.*` namespace
- **File + Console**: Simultaneous output to console and file
- **JSON Structured Logging**: Machine-parsable logs for analysis
- **Context Visibility**: See exact context sent to AI (DEBUG level)
- **Real-time Streaming**: Watch AI's thinking and tool usage live

**Example JSON Log Output**:
```json
{"timestamp": "2025-11-03T14:30:45.123Z", "level": "INFO", "logger": "alphanso.graph.nodes", "message": "NODE: validate"}
{"timestamp": "2025-11-03T14:30:45.234Z", "level": "INFO", "logger": "alphanso.graph.nodes", "message": "[1/3] Build"}
{"timestamp": "2025-11-03T14:30:50.456Z", "level": "INFO", "logger": "alphanso.graph.nodes", "message": "     ✅ Success (5.22s)"}
```

#### Debugging Tips

**View AI Context**:
```bash
# See exact system prompt and user message sent to AI
uv run alphanso run --config config.yaml -vv --log-file debug.log
grep "CONTEXT SENT TO AI" debug.log -A 50
```

**Track Failures**:
```bash
# Capture all validation failures and AI responses
uv run alphanso run --config config.yaml -v 2>&1 | tee run.log
```

**JSON Analysis**:
```bash
# Parse JSON logs with jq
uv run alphanso run --config config.yaml -v --log-file logs.json --log-format json
cat logs.json | jq 'select(.level == "ERROR")'  # Show only errors
cat logs.json | jq 'select(.logger | contains("ai_fix"))'  # Show AI actions
```

### More Examples

- **Hello World**: `examples/hello-world/` - Git merge conflict resolution with AI agent
- **Kubernetes Rebase**: Coming soon - Complex rebasing workflow
- **Dependency Upgrade**: Coming soon - Automated dependency updates

## 🏗️ Architecture

### LangGraph State Machine

Alphanso uses [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration, providing a robust state machine for the convergence loop. The framework follows a graph-based architecture:

- **State Management**: TypedDict-based state flows through graph nodes
- **Node Functions**: Pure functions that return partial state updates
- **Graph Compilation**: LangGraph compiles the workflow into an optimized execution graph
- **Type Safety**: Full mypy strict typing with proper LangGraph generics

**Current Graph Structure** (STEP 4):
```
START → pre_actions → validate → decide → {end_success, end_failure, retry}
                        ↑                           │
                        └─── ai_fix ← increment_attempt ←──┘
```

**Flow**:
1. Run pre-actions once
2. Validate current state
3. If success → END
4. If failure & attempts remain → increment attempt → invoke AI to fix → re-validate
5. If failure & max attempts → END

### Agent Configuration

Alphanso supports multiple AI agent SDKs for the convergence loop:

#### Claude Agent SDK (Default)
Production-ready agents with automatic context management, tools, and session handling.

```yaml
agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"
```

#### OpenAI Agent SDK
Lightweight agents with built-in loops, handoffs, and guardrails.

```yaml
agent:
  type: "openai-agent-sdk"
  openai:
    model: "gpt-4"
```

### Pre-Actions System

Pre-actions are commands that run **once** before the main convergence loop. They execute sequentially and set up the environment for the iterative problem-solving phase.

**Perfect for:**
- Git operations (fetch, merge, rebase)
- Container setup
- Dependency updates (go mod tidy, npm install)
- Environment initialization
- File system preparation
- Build prerequisites

**Key Features:**
- **Variable Substitution**: Use `${VAR}` syntax to inject environment variables dynamically
- **Automatic Timeout**: 600-second default timeout per action (configurable)
- **Failure Tolerance**: Continues execution even when actions fail (captured for analysis)
- **Result Capture**: Full stdout/stderr capture with exit codes
- **Idempotent Execution**: Runs only once per workflow, preventing duplicate operations

## 🧪 Development

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

