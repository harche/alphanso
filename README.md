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
- **Flexible Architecture**: Extensible workflow with state management
- **Professional Quality**: 87%+ test coverage, strict mypy typing, comprehensive tooling

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

**Expected Output**:
```
Loading configuration from: examples/hello-world/config.yaml

======================================================================
NODE: pre_actions
======================================================================
Running pre-actions to set up environment...

[1/3] Setup git repositories with conflict
     ✅ Success
     │ Creating git repositories with merge conflict...

[2/3] Fetch upstream changes
     ✅ Success

[3/3] Attempt merge (will conflict)
     ✅ Success
     │ Auto-merging README.md

======================================================================
NODE: validate
======================================================================
Running validators to check current state...

[1/1] Git Conflict Check
     ❌ Failed (0.01s)

❌ 1 validator(s) FAILED:
   - Git Conflict Check

======================================================================
NODE: decide
======================================================================
❌ Validation failed (attempt 1/5)
   Failed validators: Git Conflict Check
   Decision: RETRY (increment attempt and re-validate)
======================================================================

======================================================================
NODE: increment_attempt
======================================================================
📊 Attempt 1 → 2
   Failed validators: Git Conflict Check
   Failure history entries: 1
🔄 Retrying validation...
======================================================================

======================================================================
NODE: ai_fix
======================================================================
Invoking Claude agent to investigate and fix failures...

✅ Agent initialized
   Provider: vertex
   Model: claude-sonnet-4-5@20250929

🤖 Invoking Claude agent...

======================================================================
CLAUDE'S ACTIONS (STREAMING):
======================================================================

💭 Claude says:
   I'll investigate the git conflict markers in the README.md file and fix them.

🔧 Using tool: Read
   Input: {'file_path': 'git-repos/fork/README.md'}

💭 Claude says:
   I can see the issue clearly. The README.md file has unresolved git conflict markers.
   I'll resolve this by merging the content appropriately.

🔧 Using tool: Edit
   Input: {'file_path': 'git-repos/fork/README.md', 'old_string': '...', 'new_string': '...'}

💭 Claude says:
   Perfect! I've resolved the git conflict markers by:
   1. Removing all conflict markers
   2. Keeping the newer version (2.0.0)
   3. Merging features from both versions

======================================================================

✅ Agent invocation completed
   Stop reason: end_turn
   Tool calls: 2

======================================================================
NODE: validate
======================================================================
Running validators to check current state...

[1/1] Git Conflict Check
     ✅ Success (0.01s)

✅ All validators PASSED

======================================================================
NODE: decide
======================================================================
✅ All validators passed
   Decision: END with success
======================================================================

============================================================
✅ All pre-actions completed successfully!
============================================================
```

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
```

### Using the Python API

You can also use Alphanso programmatically. The API accepts `ConvergenceConfig` objects:

```python
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
    working_directory="."                  # Optional
)

# Check results
if result["success"]:
    print("✅ All steps succeeded!")
    for action in result["pre_action_results"]:
        status = "✅" if action["success"] else "❌"
        print(f"{status} {action['action']}")
```

The `run_convergence()` function:
- **Takes**:
  - `config`: ConvergenceConfig object
  - `system_prompt_content`: System prompt for AI agent (required)
  - `env_vars`: Optional environment variables
  - `working_directory`: Optional working directory
- **Returns**: `ConvergenceResult` with:
  - `success`: bool - Overall success status
  - `pre_action_results`: list - Results from each pre-action
  - `config_name`: str - Name from the config
  - `working_directory`: str - Working directory used

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
- ✅ Full mypy --strict typing with proper LangGraph generics

**STEP 2: Validator Base Class & Simple Validators** ✅ **COMPLETE**

- ✅ Validator abstract base class with timing and error handling
- ✅ CommandValidator for shell commands (make, test, build, etc.)
- ✅ GitConflictValidator for merge conflict detection
- ✅ create_validators() factory function
- ✅ Real validate_node implementation with progress display
- ✅ Comprehensive tests (41 tests, 100% validators coverage)
- ✅ Updated hello-world example with validators

**STEP 3: Retry Loop & Conditional Edges** ✅ **COMPLETE**

- ✅ Conditional edge routing based on validation results
- ✅ increment_attempt node for tracking iterations
- ✅ Failure history tracking across attempts
- ✅ Max attempts limit with proper termination
- ✅ Complete retry loop: validate → decide → increment_attempt → validate

**STEP 4: AI Agent Integration** ✅ **COMPLETE**

- ✅ Claude Agent SDK integration with built-in tools
- ✅ ai_fix node that invokes Claude when validation fails
- ✅ Streaming output showing Claude's thinking and tool usage
- ✅ Real-time display of tool calls (Bash, Read, Write, Edit, etc.)
- ✅ System prompt loading from config files
- ✅ Support for both Anthropic API and Vertex AI
- ✅ Autonomous problem investigation and resolution
- ✅ Updated hello-world example with full AI workflow

**Test Coverage**: 140 tests, 92% coverage

```
Name                                  Stmts   Miss Branch BrPart   Cover
------------------------------------------------------------------------
src/alphanso/actions/pre_actions.py      31      0      0      0  100.00%
src/alphanso/api.py                      31      0      4      1   97.14%
src/alphanso/cli.py                      33      0      6      0  100.00%
src/alphanso/config/schema.py            48      0      4      0  100.00%
src/alphanso/graph/builder.py            16      0      0      0  100.00%
src/alphanso/graph/nodes.py              91     28     36      5   62.99%
src/alphanso/graph/state.py              31      0      0      0  100.00%
src/alphanso/validators/base.py          16      0      0      0  100.00%
src/alphanso/validators/command.py       16      0      0      0  100.00%
src/alphanso/validators/git.py           11      0      0      0  100.00%
------------------------------------------------------------------------
TOTAL                                   330     29     50      6   87.11%
```

## 🗺️ Roadmap

Alphanso has a fully functional AI-powered convergence framework! STEP 0-4 are complete and production-ready.

### Core Framework
- [x] **STEP 0: Pre-Actions System** ✅ - Commands that run once before convergence
- [x] **STEP 1: State Schema & Graph Structure** ✅ - LangGraph workflow orchestration
- [x] **STEP 2: Validator System** ✅ - Build, test, and conflict detection
- [x] **STEP 3: Retry Loop & Conditional Edges** ✅ - Intelligent iteration control
- [x] **STEP 4: AI Agent Integration** ✅ - Claude Agent SDK with autonomous fixing
- [ ] **STEP 5: Advanced Retry Strategies** - Targeted, hybrid, and full retry modes
- [ ] **Extended Configuration System** - Advanced workflow options
- [ ] **Container Operations Support** - Podman/Docker integration
- [ ] **Multi-Agent Workflows** - Specialized agents for different tasks

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
