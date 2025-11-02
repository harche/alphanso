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
- **Multiple Agent SDKs**: Support for Claude Agent SDK and OpenAI Agent SDK
- **Variable Substitution**: Dynamic environment variable injection in commands
- **Type-Safe Configuration**: Pydantic-based YAML configuration with validation
- **Flexible Architecture**: Extensible workflow orchestration with state management
- **Professional Quality**: 96%+ test coverage, strict mypy typing, comprehensive tooling

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

The simplest way to get started is with the hello world example:

```bash
# Clone the repository
git clone <repo-url>
cd alphanso

# Install dependencies
uv sync

# Run the hello world example
uv run python examples/hello-world/run.py

# Or use the CLI
uv run alphanso run --config examples/hello-world/config.yaml
```

This example demonstrates:
- **LangGraph state machine**: See all 3 nodes executing (pre_actions → validate → decide)
- Loading configuration from YAML
- Running pre-actions with variable substitution
- Complete workflow visibility from START to END

**No external dependencies required** - just basic shell commands!

**Expected Output** (showing LangGraph nodes):
```
Loading configuration from: examples/hello-world/config.yaml

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

### Configuration Example

Here's what a simple configuration looks like (`examples/hello-world/config.yaml`):

```yaml
name: "Hello World Example"
max_attempts: 10

agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"

pre_actions:
  - command: "mkdir -p output"
    description: "Create output directory"

  - command: "echo 'Hello! Current time is ${CURRENT_TIME}' > output/greeting.txt"
    description: "Write greeting file"

  - command: "cat output/greeting.txt"
    description: "Display greeting"
```

### Using the CLI

```bash
# Run with a config file
alphanso run --config config.yaml

# Pass environment variables
alphanso run --config rebase.yaml --var K8S_TAG=v1.35.0 --var RELEASE=4.22
```

### Using as a Python Library

You can also use Alphanso programmatically using the same API that the CLI uses:

```python
from alphanso.api import run_convergence

# Run with a config file
result = run_convergence(
    config_path="config.yaml",
    env_vars={"K8S_TAG": "v1.35.0"}  # Optional environment variables
)

# Check results
if result["success"]:
    print("✅ All pre-actions succeeded!")
    for action in result["pre_action_results"]:
        print(f"  - {action['action']}")
else:
    print("❌ Some pre-actions failed")
    for action in result["pre_action_results"]:
        if not action["success"]:
            print(f"  - {action['action']}: {action['stderr']}")
```

The `run_convergence()` function returns a `ConvergenceResult` with:
- `success`: bool - Overall success status
- `pre_action_results`: list - Results from each pre-action
- `config_name`: str - Name from the config file
- `working_directory`: str - Working directory used

### More Examples

- **Hello World**: `examples/hello-world/` - Simple introduction (no dependencies)
- **Kubernetes Rebase**: Coming soon - Complex rebasing workflow
- **Dependency Upgrade**: Coming soon - Automated dependency updates

## 🏗️ Architecture

### LangGraph State Machine

Alphanso uses [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration, providing a robust state machine for the convergence loop. The framework follows a graph-based architecture:

- **State Management**: TypedDict-based state flows through graph nodes
- **Node Functions**: Pure functions that return partial state updates
- **Graph Compilation**: LangGraph compiles the workflow into an optimized execution graph
- **Type Safety**: Full mypy strict typing with proper LangGraph generics

**Current Graph Structure** (STEP 1):
```
START → pre_actions → validate → decide → END
```

Future steps will add conditional edges for retry loops and AI-powered fixing.

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

## 📊 Current Status

**STEP 0: Pre-Actions System** ✅ **COMPLETE**

- ✅ PreAction class with variable substitution and working directory support
- ✅ Pydantic configuration schema with Claude Agent SDK & OpenAI Agent SDK support
- ✅ Public API with `run_convergence()` function
- ✅ CLI interface with `alphanso run` command (thin wrapper over API)
- ✅ Professional development tooling

**STEP 1: State Schema & Graph Structure** ✅ **COMPLETE**

- ✅ Complete ConvergenceState TypedDict with all fields (pre-actions, validation, AI, metadata)
- ✅ ValidationResult TypedDict for validator outputs
- ✅ LangGraph integration with StateGraph and graph compilation
- ✅ Graph builder with linear flow: START → pre_actions → validate → decide → END
- ✅ Placeholder nodes for validate and decide (ready for STEP 2 & 3)
- ✅ Full mypy --strict typing with proper LangGraph generics

**Test Coverage**: 76 tests, 97.33% coverage

```
Name                                  Stmts   Miss   Cover
---------------------------------------------------------
src/alphanso/actions/pre_actions.py      31      0  100.00%
src/alphanso/api.py                      31      0   97.14%
src/alphanso/cli.py                      54      1   97.14%
src/alphanso/config/schema.py            41      0  100.00%
src/alphanso/graph/builder.py            14      0  100.00%
src/alphanso/graph/nodes.py              24      1   91.18%
src/alphanso/graph/state.py              31      0  100.00%
---------------------------------------------------------
TOTAL                                   228      3   97.33%
```

## 🗺️ Roadmap

Alphanso is under active development. STEP 0 (Pre-Actions) and STEP 1 (Graph Structure) are complete and production-ready. The next phases will add validators, retry logic, and AI agent integration.

### Core Framework
- [x] **STEP 0: Pre-Actions System** ✅ - Commands that run once before convergence
- [x] **STEP 1: State Schema & Graph Structure** ✅ - LangGraph workflow orchestration
- [ ] **STEP 2: Validator System** - Build, test, and conflict detection
- [ ] **STEP 3: Retry Loop & Conditional Edges** - Intelligent iteration control
- [ ] **Investigation & Fixing Tools** - AI-powered problem analysis
- [ ] **AI Agent Integration** - Claude/OpenAI agent orchestration
- [ ] **Extended Configuration System** - Advanced workflow options
- [ ] **Container Operations Support** - Podman/Docker integration
- [ ] **Targeted Retry Strategy** - Smart failure tracking and recovery
- [ ] **CLI Interface** - `alphanso` command-line tool

### Use Case Examples
- [ ] **Dependency Upgrade Example** - Automated package updates
- [ ] **Complex Rebasing Examples** - Kubernetes/OpenShift fork maintenance

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Inspired by the [rebaser project](https://github.com/openshift/kubernetes/tree/master/openshift-hack/rebaser) for Kubernetes rebasing.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

[Add your contact information here]
