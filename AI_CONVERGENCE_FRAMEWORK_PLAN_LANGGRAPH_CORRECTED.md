# Alphanso - Implementation Plan (LangGraph + Claude Agent SDK)

## Overview

Build a Python-based framework for AI-assisted iterative problem resolution using **LangGraph** for workflow orchestration and **Claude Agent SDK** for AI execution. The framework validates conditions (build, test, etc.), and when validation fails, invokes Claude with investigation/fixing tools. This iterates until convergence or max attempts.

**Key Use Cases:**
- Kubernetes rebasing (rebase openshift fork of kubernetes with upstream kubernetes)
- Dependency upgrades (upgrade → test → fix breaks → iterate)
- Code refactoring (refactor → lint → test → fix issues → iterate)
- Database migrations (migrate → validate → fix conflicts → iterate)
- Infrastructure updates (update → deploy → validate → fix → iterate)
- Security patching (patch → build → test → fix regressions → iterate)

## Architecture Overview

```
Entry Point: alphanso run --config rebase.yaml --var K8S_TAG=v1.35.0
       ↓
┌─────────────────────────────────────────────────────────────┐
│  PRE-ACTIONS PHASE (Setup before convergence loop)         │
│  - Git operations (fetch, merge upstream tag)               │
│  - Container setup                                          │
│  - Initial dependency updates (go mod tidy)                 │
│  - Any other setup actions                                  │
│  These run ONCE, failures here enter convergence loop       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│         LangGraph State Graph (Convergence Loop)            │
│  (Orchestration, Routing, State Management)                 │
│                                                              │
│  ┌──────┐    ┌─────────────┐    ┌────────┐                │
│  │START │───▶│  Validate   │───▶│ Decide │                │
│  └──────┘    │ (run make,  │    └───┬────┘                │
│              │  make test) │        │                       │
│              └─────────────┘        ▼                       │
│                     ▲         ┌──────────┐                 │
│                     │         │ Success? │                 │
│                     │         └─┬──────┬─┘                 │
│                     │          No    Yes                    │
│                     │           │     │                     │
│                     │           │     ▼                     │
│                     │           │  ┌─────┐                 │
│                     │           │  │ END │                 │
│                     │           │  │SUCCESS│               │
│                     │           │  └─────┘                 │
│                     │           │                           │
│                     │           ▼                           │
│                     │    ┌──────────────┐                  │
│                     │    │ Max Attempts?│                  │
│                     │    └─┬──────────┬─┘                  │
│                     │     No        Yes                     │
│                     │      │          │                     │
│                     │      │          ▼                     │
│                     │      │       ┌──────┐                │
│                     │      │       │FAILED│                │
│                     │      │       └──────┘                │
│                     │      │                                │
│                     │      ▼                                │
│              ┌──────┴────────┐                             │
│              │   AI Fix      │                             │
│              │ (Claude Agent)│                             │
│              └───────────────┘                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│       Claude Agent SDK                                      │
│  (AI Execution with Built-in SDK Tools)                     │
│                                                              │
│  SDK Built-in Tools for INVESTIGATION and FIXING:           │
│  - Bash: Execute ANY command (git, gh, make, grep, etc.)    │
│  - Read: Read file contents                                 │
│  - Edit: Edit files by replacing content                    │
│  - Grep: Search code with regex                             │
│  - Glob: Find files matching patterns                       │
│                                                              │
│  These tools help Claude UNDERSTAND and FIX issues,         │
│  but Claude does NOT run validators (make, make test)       │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│       Validators (SEPARATE from AI Tools)                   │
│  (Run by graph's Validate node, OUTSIDE AI control)         │
│                                                              │
│  - GitConflictValidator → git diff --check                  │
│  - BuildValidator → make                                    │
│  - TestValidator → make test                                │
│  - ContainerOpsValidator → podman exec ... make update      │
│                                                              │
│  These are CONDITIONS we check, not tools for Claude!       │
└─────────────────────────────────────────────────────────────┘
```

## Entry Point & Pre-Actions

**How it works:**

1. **User runs command:**
   ```bash
   ai-convergence run --config rebase.yaml --var K8S_TAG=v1.35.0
   ```

2. **Pre-actions execute** (defined in config):
   ```yaml
   pre_actions:
     - git fetch upstream
     - git merge upstream/${K8S_TAG}
     - ./setup-container.sh
     - go mod tidy
   ```

3. **Pre-action outcomes:**
   - ✅ **All pass**: Enter validation loop (might still pass immediately)
   - ❌ **Any fail**: Enter convergence loop with failures

4. **Convergence loop:**
   - Run validators (make, make test, etc.)
   - If failures → Claude investigates and fixes
   - Re-validate → Repeat until success or max attempts

**Example for Kubernetes rebase:**
```bash
# User runs
./rebase.sh v1.35.0-alpha.2 release-4.22

# rebase.sh calls framework
alphanso run \
  --config k8s-rebase.yaml \
  --var K8S_TAG=v1.35.0-alpha.2 \
  --var OPENSHIFT_RELEASE=release-4.22

# Pre-actions run (git merge, etc.)
# If merge conflicts → enters convergence loop
# Claude fixes conflicts → validators re-run → iterate
```

## **Critical Architecture Principle**

**SEPARATION OF CONCERNS:**

1. **Validators** (make, make test, git conflicts) = **WHAT we check**
   - Run in the `validate_node` by the framework
   - NOT exposed to Claude as tools
   - Results passed to Claude as context

2. **SDK Built-in Tools** (Bash, Read, Edit, Grep, Glob) = **HOW Claude investigates and fixes**
   - Provided by Claude Code Agent SDK
   - Bash tool covers ALL commands (git, gh, make, etc.)
   - Used to understand failures and apply fixes
   - Claude uses these to make changes

**Flow:**
```
Validate Node (Framework runs validators)
    ↓
  Failed? → AI Fix Node (Claude uses SDK tools)
    ↓              ↓
Success!    Changes made → Loop back to Validate
```

**Claude never runs `make` or `make test`** - it uses SDK's Read, Edit tools and Bash tool (for git, gh commands) to understand and fix issues. Then the framework re-runs validators.

## Project Structure

```
alphanso/
├── src/alphanso/
│   ├── __init__.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py              # State schema (TypedDict)
│   │   ├── nodes.py              # Graph nodes (validate, ai_fix, decide)
│   │   ├── edges.py              # Conditional edges
│   │   └── builder.py            # Graph construction
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── client.py             # Claude Agent SDK wrapper
│   │   ├── tools.py              # AI tools (git, file ops, NOT validators)
│   │   └── prompts.py            # System prompts
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── base.py               # Base validator class
│   │   ├── command.py            # Shell command validator
│   │   ├── git.py                # Git conflict validator
│   │   ├── test_suite.py         # Test runner with retry
│   │   └── container.py          # Container operations validator
│   ├── config/
│   │   ├── __init__.py
│   │   └── schema.py             # Configuration models (Pydantic)
│   ├── cli.py
│   └── utils/
│       ├── __init__.py
│       ├── logging.py            # Structured logging
│       └── output.py             # Progress display
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── examples/
│   ├── 01_simple_validation/
│   ├── 02_command_retry/
│   ├── 03_dependency_upgrade/
│   └── 04_kubernetes_rebase/
├── pyproject.toml
└── docs/
```

## Dependencies

```toml
[project]
name = "alphanso"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",           # State graph orchestration
    "anthropic>=0.40.0",          # Claude Agent SDK
    "pydantic>=2.0.0",            # Configuration validation
    "pyyaml>=6.0.0",              # YAML config support
    "click>=8.0.0",               # CLI framework
    "rich>=13.0.0",               # Beautiful terminal output
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.8.0",
    "black>=24.0.0",
    "isort>=5.13.0",
]
```

## Implementation Steps

### **STEP 0: Pre-Actions System** ✅ COMPLETED

**Status**: ✅ **COMPLETE** - All deliverables implemented, tested, and verified (55 tests, 96.88% coverage)

**Goal**: Implement pre-actions that run before convergence loop (git merge, setup, etc.)

**Deliverables**:
- `PreAction` class for running setup commands
- Pre-actions configuration schema
- `pre_actions_node` for graph
- Variable substitution in pre-actions
- Proper error handling (continue on failures)

**Files to Create**:
- `src/alphanso/actions/pre_actions.py`
- `tests/unit/test_pre_actions.py`

**Pre-Action Class**:
```python
import subprocess
import re
from typing import Dict, Any

class PreAction:
    """Execute pre-actions (setup commands before convergence loop)."""

    def __init__(self, command: str, description: str = ""):
        self.command = command
        self.description = description or command

    def run(self, env_vars: Dict[str, str]) -> PreActionResult:
        """
        Run pre-action with variable substitution.

        Variables are substituted as ${VAR_NAME}.
        Failures are captured but don't stop execution.
        """
        # Substitute variables
        expanded_command = self._substitute_vars(self.command, env_vars)

        # Run command
        start = time.time()
        try:
            result = subprocess.run(
                expanded_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout for pre-actions
            )

            return PreActionResult(
                action=self.description,
                success=result.returncode == 0,
                output=result.stdout[-1000:],  # Last 1000 chars
                stderr=result.stderr[-1000:],
                exit_code=result.returncode,
                duration=time.time() - start
            )
        except Exception as e:
            return PreActionResult(
                action=self.description,
                success=False,
                output="",
                stderr=str(e),
                exit_code=None,
                duration=time.time() - start
            )

    def _substitute_vars(self, text: str, env_vars: Dict[str, str]) -> str:
        """Replace ${VAR} with env_vars['VAR']."""
        pattern = r'\$\{(\w+)\}'
        def replacer(match):
            var_name = match.group(1)
            return env_vars.get(var_name, match.group(0))
        return re.sub(pattern, replacer, text)
```

**Pre-Actions Node** (for graph):
```python
def pre_actions_node(state: ConvergenceState) -> ConvergenceState:
    """
    Run pre-actions before entering convergence loop.

    Examples: git merge, container setup, go mod tidy

    Failures are captured but don't stop execution -
    they'll be caught in the validation phase.
    """
    if state["pre_actions_completed"]:
        return state  # Skip if already done

    results = []

    # Get environment variables from state
    env_vars = {
        "K8S_TAG": state.get("k8s_tag", ""),
        "OPENSHIFT_RELEASE": state.get("openshift_release", ""),
        "KUBE_REPO": state.get("working_directory", ""),
        # ... other vars
    }

    # Run each pre-action
    for action_config in state["pre_actions_config"]:
        pre_action = PreAction(
            command=action_config["command"],
            description=action_config.get("description", "")
        )

        result = pre_action.run(env_vars)
        results.append(result)

        # Log but continue even on failures
        if not result["success"]:
            print(f"⚠️  Pre-action failed: {result['action']}")
            print(f"   {result['stderr']}")

    return {
        **state,
        "pre_actions_completed": True,
        "pre_action_results": results
    }
```

**Test Cases**:
1. PreAction runs command successfully
2. PreAction substitutes variables correctly
3. PreAction handles command failures
4. PreAction respects timeout
5. Pre-actions node runs all actions
6. Pre-actions node continues on failures
7. Pre-actions node runs only once
8. Variable substitution works with multiple vars
9. Pre-action results are captured in state
10. Type checking passes

**Success Criteria**:
- ✅ All 10 test cases pass
- ✅ Pre-actions run before validation
- ✅ Failures don't stop execution
- ✅ Type checking passes
- ✅ Code coverage ≥ 90%

**Implementation Summary** (Completed):

**Files Created**:
- ✅ `src/alphanso/actions/pre_actions.py` - PreAction class with variable substitution and working directory support
- ✅ `src/alphanso/graph/nodes.py` - pre_actions_node for graph integration
- ✅ `src/alphanso/graph/state.py` - ConvergenceState TypedDict
- ✅ `src/alphanso/config/schema.py` - Pydantic configuration with Claude/OpenAI agent support
- ✅ `src/alphanso/api.py` - Public API with run_convergence() function
- ✅ `src/alphanso/cli.py` - CLI interface (thin wrapper over API)
- ✅ `tests/unit/test_pre_actions.py` - 15 comprehensive test cases
- ✅ `tests/unit/test_api.py` - 11 API integration tests
- ✅ `tests/unit/test_cli.py` - CLI tests
- ✅ `examples/hello-world/` - Working example with no external dependencies

**Additional Features Implemented**:
- ✅ Working directory support - pre-actions execute in config file's parent directory
- ✅ Public API layer - both CLI and library users call same run_convergence() function
- ✅ Automatic CURRENT_TIME variable injection
- ✅ Comprehensive error handling and timeout support (600s default)
- ✅ Output truncation (last 1000 chars) for large outputs
- ✅ Idempotent execution (runs only once per workflow)

**Test Results**:
- 55 tests passing (15 PreAction + 11 API + 14 CLI + 15 other)
- 96.88% code coverage
- All type checking passing (mypy --strict)
- All tests complete in <1 second

**Examples Working**:
- ✅ `examples/hello-world/` - Demonstrates variable substitution and working directory
- Files created in correct location (examples/hello-world/output/)
- Clean CLI output with success indicators

**Ready For**: STEP 1 - State Schema & Basic Graph Structure

---

### **STEP 1: State Schema & Basic Graph Structure** ✅ COMPLETED

**Status**: ✅ **COMPLETE** - All deliverables implemented, tested, and verified (76 tests, 97.33% coverage)

**Goal**: Define LangGraph state and create minimal working graph (no validators, no AI)

**Deliverables**:
- `ConvergenceState` TypedDict with all fields
- Basic `StateGraph` with START → pre_actions → validate → decide → END
- Placeholder nodes (validate_node, decide_node)
- Graph compilation and execution
- Type checking with mypy strict
- Real-time node execution visibility

**Files Created**:
- `src/alphanso/graph/state.py` - Complete state schema with ValidationResult and ConvergenceState (22 fields)
- `src/alphanso/graph/nodes.py` - pre_actions_node, validate_node (placeholder), decide_node (placeholder)
- `src/alphanso/graph/builder.py` - Graph builder with ConvergenceGraph type alias
- `tests/unit/test_state.py` - 10 comprehensive state tests
- `tests/unit/test_graph.py` - 11 graph integration tests
- Updated `examples/hello-world/run.py` - Demonstrates LangGraph execution

**State Schema**:
```python
from typing import TypedDict, List, Dict, Optional, Any
from dataclasses import dataclass

class ValidationResult(TypedDict):
    """Result from a single validator (run by framework, NOT AI)."""
    validator_name: str
    success: bool
    output: str
    stderr: str
    exit_code: Optional[int]
    duration: float
    timestamp: float
    metadata: Dict[str, Any]  # e.g., {"failing_packages": [...]}

class PreActionResult(TypedDict):
    """Result from a pre-action."""
    action: str
    success: bool
    output: str
    stderr: str
    exit_code: Optional[int]
    duration: float

class ConvergenceState(TypedDict):
    """State for the convergence loop."""
    # Pre-actions (run once at start)
    pre_actions_completed: bool
    pre_action_results: List[PreActionResult]

    # Loop control
    attempt: int
    max_attempts: int
    success: bool

    # Current validation results (from framework-run validators)
    validation_results: List[ValidationResult]
    failed_validators: List[str]

    # Failure history across attempts
    failure_history: List[List[ValidationResult]]

    # AI interaction (tools used, changes made)
    agent_session_id: Optional[str]
    agent_tool_calls: List[Dict[str, Any]]  # Track what Claude did
    agent_messages: List[str]  # Conversation history

    # Configuration
    pre_actions_config: List[str]  # Commands to run before loop
    validators_config: List[Dict]
    ai_tools_config: Dict  # Configuration for AI tools
    retry_strategy: str

    # Metadata
    start_time: float
    total_duration: float
    working_directory: str
```

**Basic Graph** (with pre-actions):
```python
from langgraph.graph import StateGraph, START, END

def create_convergence_graph() -> StateGraph:
    """Create the convergence state graph."""
    graph = StateGraph(ConvergenceState)

    # Add nodes
    graph.add_node("pre_actions", pre_actions_node)  # NEW: Setup phase
    graph.add_node("validate", validate_node)
    graph.add_node("decide", decide_node)

    # Add edges
    graph.add_edge(START, "pre_actions")  # Start with setup
    graph.add_edge("pre_actions", "validate")  # Then validate
    graph.add_edge("validate", "decide")
    graph.add_edge("decide", END)

    return graph.compile()

def pre_actions_node(state: ConvergenceState) -> ConvergenceState:
    """
    Run pre-actions (git merge, setup, etc.).
    These run ONCE before entering the convergence loop.
    """
    if state["pre_actions_completed"]:
        return state  # Already done

    results = []
    for action in state["pre_actions_config"]:
        # Run action (e.g., "git merge upstream/${K8S_TAG}")
        # Substitute variables
        expanded_action = substitute_vars(action, state)

        result = run_command(expanded_action)
        results.append(result)

        # Continue even if failures (they'll be caught in validation)

    return {
        **state,
        "pre_actions_completed": True,
        "pre_action_results": results
    }

def validate_node(state: ConvergenceState) -> ConvergenceState:
    """Run validators (FRAMEWORK runs them, not AI)."""
    # For now, just succeed
    return {
        **state,
        "success": True,
        "validation_results": []
    }

def decide_node(state: ConvergenceState) -> ConvergenceState:
    """Simple decision node."""
    return state
```

**Test Cases**:
1. State schema is valid TypedDict
2. Graph compiles successfully
3. Graph executes from START to END
4. State is properly threaded through nodes
5. Type checking passes (mypy)
6. Basic graph execution takes <100ms
7. State updates are immutable (no mutation)

**Success Criteria**:
- ✅ All test cases pass (76 total tests)
- ✅ `mypy --strict` passes with no errors on 12 source files
- ✅ Graph runs end-to-end with visible node execution
- ✅ Code coverage 97.33% (exceeds 95% target)

**Implementation Summary**:

**State Schema** (`src/alphanso/graph/state.py`):
- ✅ `ValidationResult` TypedDict with 8 fields (validator results)
- ✅ `ConvergenceState` TypedDict with 22 fields total:
  - Pre-actions: `pre_actions_completed`, `pre_action_results`, `pre_actions_config`
  - Loop control: `attempt`, `max_attempts`, `success`
  - Validation: `validation_results`, `failed_validators`, `failure_history`
  - AI interaction: `agent_session_id`, `agent_tool_calls`, `agent_messages`
  - Configuration: `validators_config`, `ai_tools_config`, `retry_strategy`
  - Environment: `working_directory`, `env_vars`
  - Metadata: `start_time`, `total_duration`
- ✅ Used `TypedDict` with `total=False` for partial state updates from nodes
- ✅ Full mypy strict typing with proper generics

**Graph Builder** (`src/alphanso/graph/builder.py`):
- ✅ `ConvergenceGraph` type alias for clarity (replaces confusing repeated generics)
- ✅ `create_convergence_graph()` returns properly typed CompiledStateGraph
- ✅ Linear flow: START → pre_actions → validate → decide → END
- ✅ Clean comments explaining LangGraph type parameters

**Graph Nodes** (`src/alphanso/graph/nodes.py`):
- ✅ `pre_actions_node`: Executes setup commands with real-time progress display
  - Shows `[1/5] Action name` with ✅/❌ status
  - Captures and displays output for each action
  - Continues on failures (idempotent execution)
- ✅ `validate_node`: Placeholder that sets `success = True`
  - Prints "Running validators (placeholder - STEP 2 will implement)"
  - Ready for validator integration in STEP 2
- ✅ `decide_node`: Placeholder that returns empty dict
  - Prints "Making decision (placeholder - STEP 3 will implement)"
  - Ready for conditional logic in STEP 3
- ✅ All nodes print banners showing execution flow

**Node Visibility Enhancement**:
- ✅ Each node prints clear banner (NODE: name) when executing
- ✅ Pre-actions show real-time progress: `[1/5] Description → ✅ Success`
- ✅ Both CLI and Python script show full LangGraph execution
- ✅ Removed redundant CLI output (nodes print directly)

**Integration with API** (`src/alphanso/api.py`):
- ✅ `run_convergence()` uses `create_convergence_graph()`
- ✅ Graph invoked with proper initial state
- ✅ Returns ConvergenceResult with all pre-action results

**Test Coverage**:
- ✅ `tests/unit/test_state.py`: 10 tests for state schema
  - ValidationResult structure and all fields
  - ConvergenceState with all 22 fields
  - Partial field support (TypedDict total=False)
  - Field immutability patterns
- ✅ `tests/unit/test_graph.py`: 11 tests for graph execution
  - Graph compilation
  - End-to-end execution
  - State threading through nodes
  - Performance (<100ms)
  - State immutability
  - Pre-actions integration
- ✅ Updated `test_cli.py`: Fixed test to check for "NODE: pre_actions" instead of removed header

**Example Updates**:
- ✅ `examples/hello-world/run.py`: Shows LangGraph node execution
- ✅ `examples/hello-world/README.md`: Documents node execution flow
- ✅ Main `README.md`: Updated with STEP 1 completion status and LangGraph output

**Type Safety Improvements**:
- ✅ Created `ConvergenceGraph` type alias to replace confusing `CompiledStateGraph[ConvergenceState, None, ConvergenceState, ConvergenceState]`
- ✅ Added clear comments explaining LangGraph's 4 type parameters: [StateT, ContextT, InputT, OutputT]
- ✅ All 12 source files pass `mypy --strict` with no errors

**Test Results**:
- 76 tests passing (21 new tests for STEP 1)
- 97.33% code coverage
- All tests complete in <1 second
- Full mypy strict compliance

**Ready For**: STEP 2 - Validator System

---

### **STEP 2: Validator Base Class & Simple Validators** ✅ COMPLETED

**Status**: ✅ **COMPLETE** - All deliverables implemented, tested, and verified (117 tests, 86.63% coverage)

**Goal**: Create validator abstraction and implement basic validators

**IMPORTANT**: Validators are NOT AI tools. They are conditions we check. The framework runs them in the `validate_node`.

**Deliverables**:
- ✅ `Validator` base class with timing and error handling
- ✅ `CommandValidator` - runs shell commands (make, make test)
- ✅ `GitConflictValidator` - checks for merge conflicts
- ✅ Integration into graph's validate node with real-time progress
- ✅ Proper error handling and timeouts
- ✅ Factory function for validator creation
- ✅ Updated hello-world example with 4 validators

**Files Created**:
- ✅ `src/alphanso/validators/__init__.py` - Public validator API exports
- ✅ `src/alphanso/validators/base.py` - Abstract Validator base class
- ✅ `src/alphanso/validators/command.py` - CommandValidator implementation
- ✅ `src/alphanso/validators/git.py` - GitConflictValidator implementation
- ✅ `tests/unit/test_validators.py` - 22 comprehensive unit tests
- ✅ `tests/integration/test_command_validator.py` - 19 integration tests with real commands

**Files Modified**:
- ✅ `src/alphanso/config/schema.py` - Added ValidatorConfig Pydantic model
- ✅ `src/alphanso/graph/nodes.py` - Added create_validators() factory and real validate_node implementation
- ✅ `src/alphanso/api.py` - Refactored to accept only ConvergenceConfig objects (no YAML knowledge)
- ✅ `examples/hello-world/config.yaml` - Added 4 validators demonstration
- ✅ `examples/hello-world/run.py` - Updated with validator results display
- ✅ `examples/hello-world/README.md` - Documented validator execution
- ✅ Main `README.md` - Updated with STEP 2 completion and API examples

**Base Validator**:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import time

class Validator(ABC):
    """
    Base class for all validators.

    Validators are CONDITIONS we check (build, test, conflicts, etc.).
    They are RUN BY THE FRAMEWORK in the validate_node.
    They are NOT tools for the AI agent.
    """

    def __init__(self, name: str, timeout: float = 600.0):
        self.name = name
        self.timeout = timeout

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Run validation and return result."""
        pass

    def run(self) -> ValidationResult:
        """Run validator with timing."""
        start = time.time()
        try:
            result = self.validate()
            result["duration"] = time.time() - start
            result["timestamp"] = start
            return result
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                success=False,
                output="",
                stderr=str(e),
                exit_code=None,
                duration=time.time() - start,
                timestamp=start,
                metadata={}
            )
```

**Command Validator** (runs make, make test, etc.):
```python
import subprocess
from typing import Optional

class CommandValidator(Validator):
    """
    Validates by running a shell command.

    Examples: make, make test, go test ./...
    This is run by the FRAMEWORK, not by Claude.
    """

    def __init__(
        self,
        name: str,
        command: str,
        timeout: float = 600.0,
        capture_lines: int = 100
    ):
        super().__init__(name, timeout)
        self.command = command
        self.capture_lines = capture_lines

    def validate(self) -> ValidationResult:
        """Run command and check exit code."""
        result = subprocess.run(
            self.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )

        # Capture last N lines
        stdout_lines = result.stdout.split('\n')
        stderr_lines = result.stderr.split('\n')

        return ValidationResult(
            validator_name=self.name,
            success=result.returncode == 0,
            output='\n'.join(stdout_lines[-self.capture_lines:]),
            stderr='\n'.join(stderr_lines[-self.capture_lines:]),
            exit_code=result.returncode,
            duration=0.0,  # Will be set by run()
            timestamp=0.0,  # Will be set by run()
            metadata={}
        )
```

**Updated Validate Node**:
```python
def validate_node(state: ConvergenceState) -> ConvergenceState:
    """
    Execute all validators.

    IMPORTANT: This node runs validators directly.
    Validators are NOT given to Claude as tools.
    """
    results = []
    failed = []

    # Create validators from config
    validators = create_validators(state["validators_config"])

    # Run each validator (FRAMEWORK runs them, not AI)
    for validator in validators:
        result = validator.run()
        results.append(result)

        if not result["success"]:
            failed.append(result["validator_name"])

    # Update state
    return {
        **state,
        "validation_results": results,
        "failed_validators": failed,
        "success": len(failed) == 0
    }
```

**Implementation Summary** (Completed):

**Validator Architecture**:
- ✅ Abstract base class (ABC) with `@abstractmethod validate()`
- ✅ Base `run()` method provides timing and universal error handling
- ✅ All exceptions caught and converted to ValidationResult
- ✅ Timeout support via subprocess (600s default)
- ✅ Working directory support for all validators
- ✅ Output truncation (last N lines) to prevent memory issues

**CommandValidator Capabilities**:
- ✅ Executes arbitrary shell commands via subprocess
- ✅ Captures stdout and stderr separately
- ✅ Configurable line capture (default 100 lines)
- ✅ Full timeout support with subprocess.TimeoutExpired handling
- ✅ Exit code checking (0 = success)
- ✅ Working directory support for commands
- ✅ Shell features supported (pipes, redirection, environment variables)

**GitConflictValidator Implementation**:
- ✅ Uses `git diff --check` to detect merge conflicts
- ✅ Parses output for conflict markers (<<<<<<, ======, >>>>>>)
- ✅ Returns detailed conflict information in metadata
- ✅ Works in any Git repository directory
- ✅ Fast execution (<100ms typical)

**Factory Function Design** (`create_validators()`):
- ✅ Type-based validator instantiation from config
- ✅ Supports "command" and "git-conflict" validator types
- ✅ Working directory propagation to all validators
- ✅ Clean error handling for unknown validator types
- ✅ Returns list of instantiated Validator objects

**Real validate_node Implementation**:
- ✅ Real-time progress display with validator count ([1/4], [2/4]...)
- ✅ Shows validator name and timing for each execution
- ✅ Visual success/failure indicators (✅/❌)
- ✅ Collects all validation results in state
- ✅ Tracks failed validator names for retry logic
- ✅ Sets overall success flag based on all validators passing
- ✅ Executes validators sequentially (not in parallel)

**API Refactoring** (Critical Architecture Change):
- ✅ `run_convergence()` now accepts ONLY ConvergenceConfig objects
- ✅ Removed all Path/YAML loading logic from API layer
- ✅ CLI layer handles config loading before calling API
- ✅ Clean separation: Config schema (structure) → CLI (I/O) → API (business logic)
- ✅ API is now a pure function, completely agnostic to config source
- ✅ Users can create config from YAML, JSON, database, or programmatically
- ✅ Updated all README examples to show programmatic config creation
- ✅ Fixed 4 failing tests that used old `config_path` parameter

**Test Coverage**:
- ✅ `tests/unit/test_validators.py`: 22 unit tests
  - Validator base class behavior
  - CommandValidator with various commands
  - GitConflictValidator detection logic
  - Error handling and exceptions
  - Timeout behavior
  - Output truncation
  - Type checking and mypy compliance
- ✅ `tests/integration/test_command_validator.py`: 19 integration tests
  - Real shell commands: echo, ls, grep, cat
  - Exit code checking (0 and non-zero)
  - Timeout testing with sleep commands
  - Output capture verification
  - stderr capture
  - Working directory changes
  - Command chaining with pipes
  - Environment variable expansion
  - File redirection (>, >>)
  - Complex multi-line output

**Examples Updated**:
- ✅ `examples/hello-world/config.yaml`: Added 4 validators
  1. Check Greeting File Exists (test -f)
  2. Verify Greeting Content (grep)
  3. Check Directory Structure (test -d)
  4. Git Conflict Check (git-conflict validator)
- ✅ `examples/hello-world/run.py`: Added validator results display
- ✅ `examples/hello-world/README.md`: Documented validator execution with expected output

**Test Results**:
- 117 tests passing (41 new validator tests + 76 existing tests)
- 86.63% code coverage (exceeds 85% target)
- 100% coverage on validator module (base.py, command.py, git.py)
- Mypy strict passing on all 12 source files
- All tests complete in <2 seconds
- CLI verified working with hello-world example
- API verified working with programmatic config creation

**Test Cases**:
1. ✅ CommandValidator succeeds with exit code 0
2. ✅ CommandValidator fails with non-zero exit
3. ✅ CommandValidator respects timeout
4. ✅ CommandValidator captures last N lines correctly
5. ✅ GitConflictValidator detects conflict markers
6. ✅ GitConflictValidator passes when resolved
7. ✅ Multiple validators run in sequence
8. ✅ Validator exceptions are caught and returned as failures
9. ✅ Timing information is accurate
10. ✅ Validators run independently (not as AI tools)

**Success Criteria**:
- ✅ All 10 test cases pass
- ✅ Integration tests with real commands pass (19 tests)
- ✅ Type checking passes (mypy --strict)
- ✅ Code coverage 86.63% (exceeds 85% target)
- ✅ Clear separation: validators ≠ AI tools
- ✅ API is pure function with no YAML knowledge
- ✅ CLI and API both verified working

**Ready For**: STEP 3 - Conditional Edges & Retry Loop

---

### **STEP 3: Conditional Edges & Retry Loop** ✅ COMPLETED

**Status**: ✅ **COMPLETE** - All deliverables implemented, tested, and verified (126 tests, 94.56% coverage)

**Goal**: Add graph routing to create the retry loop (still **without AI** - mechanical retries only)

**IMPORTANT**: This step adds the convergence loop but does NOT add AI fixing. Validators fail → retry → validators fail again. The loop is purely mechanical until STEP 5 adds Claude Agent.

**Deliverables**:
- ✅ Conditional edge function (`should_continue`) with 3 routing paths
- ✅ `increment_attempt_node` for tracking loop iterations
- ✅ Updated graph structure with conditional routing
- ✅ Retry loop logic (validate → decide → retry or end)
- ✅ Failure history tracking in validate_node
- ✅ Max attempts enforcement
- ✅ Multiple exit paths (end_success, end_failure, retry)

**Files Created**:
- ✅ `src/alphanso/graph/edges.py` - Conditional edge logic with should_continue()

**Files Modified**:
- ✅ `src/alphanso/graph/builder.py` - Added conditional edges and increment_attempt node
- ✅ `src/alphanso/graph/nodes.py` - Added increment_attempt_node() and failure history tracking
- ✅ `tests/unit/test_graph.py` - Added 9 comprehensive retry loop tests

**Conditional Edge Function** (`edges.py`):
```python
from typing import Literal
from alphanso.graph.state import ConvergenceState

EdgeDecision = Literal["end_success", "end_failure", "retry"]

def should_continue(state: ConvergenceState) -> EdgeDecision:
    """Determine next step based on validation results.

    Returns:
        "end_success" - All validators passed, workflow complete
        "end_failure" - Max attempts reached without success
        "retry" - Validators failed, continue to next attempt

    Flow:
        validate → decide → should_continue() →
            ├─ "end_success" → END (success=True)
            ├─ "end_failure" → END (success=False)
            └─ "retry" → increment_attempt → validate (loop)
    """
    # Success - all validators passed
    if state["success"]:
        return "end_success"

    # Max attempts reached - give up
    if state["attempt"] >= state["max_attempts"] - 1:
        return "end_failure"

    # Validators failed but attempts remain - retry
    return "retry"
```

**Increment Attempt Node** (`nodes.py`):
```python
def increment_attempt_node(state: ConvergenceState) -> dict[str, Any]:
    """Increment attempt counter for retry loop.

    This node runs after validation failures when retrying.
    It increments the attempt counter to track loop iterations.

    Note: Failure history is tracked by validate_node, not here.
    This ensures all validation attempts (including the last one)
    are recorded in failure_history.
    """
    new_attempt = state["attempt"] + 1
    failure_history = state.get("failure_history", [])

    print(f"📊 Attempt {state['attempt'] + 1} → {new_attempt + 1}")
    print(f"   Failed validators: {', '.join(state.get('failed_validators', []))}")
    print(f"   Failure history entries: {len(failure_history)}")
    print("🔄 Retrying validation...")

    return {
        "attempt": new_attempt,
    }
```

**Updated Graph Structure** (`builder.py`):
```python
def create_convergence_graph() -> ConvergenceGraph:
    """Create and compile the convergence state graph.

    The graph structure with STEP 3 retry loop:

    START → pre_actions → validate → decide → {end_success, end_failure, retry}
                            ↑                           │
                            └─ increment_attempt ←──────┘

    Conditional routing from decide node:
    - "end_success": All validators passed → END (success)
    - "end_failure": Max attempts reached → END (failure)
    - "retry": Validators failed, attempts remain → increment_attempt → validate
    """
    graph = StateGraph(ConvergenceState)

    # Add nodes
    graph.add_node("pre_actions", pre_actions_node)
    graph.add_node("validate", validate_node)
    graph.add_node("decide", decide_node)
    graph.add_node("increment_attempt", increment_attempt_node)  # NEW: STEP 3

    # Add linear edges (setup phase)
    graph.add_edge(START, "pre_actions")
    graph.add_edge("pre_actions", "validate")
    graph.add_edge("validate", "decide")

    # Add conditional edges (STEP 3: retry loop logic)
    graph.add_conditional_edges(
        "decide",
        should_continue,
        {
            "end_success": END,
            "end_failure": END,
            "retry": "increment_attempt",
        },
    )

    # Add retry loop edge (STEP 3: completes the cycle)
    graph.add_edge("increment_attempt", "validate")

    return graph.compile()
```

**Failure History Tracking** (added to `validate_node`):
```python
def validate_node(state: ConvergenceState) -> dict[str, Any]:
    """Execute all validators with real-time progress display."""
    # ... run validators ...

    # Update failure history if validators failed
    # This ensures every validation attempt is recorded, even the last one
    updated_history = list(state.get("failure_history", []))
    if not success:
        updated_history.append(validation_results)

    return {
        "success": success,
        "validation_results": validation_results,
        "failed_validators": failed_validators,
        "failure_history": updated_history,  # NEW: Track all failures
    }
```

**Implementation Summary** (Completed):

**Graph Transformation**:
- ✅ Changed from linear flow (START → END) to looping flow with conditional edges
- ✅ Added `increment_attempt` node to track retry iterations
- ✅ Added conditional edges from `decide` node with 3 routing paths
- ✅ Created complete loop: validate → decide → increment_attempt → validate
- ✅ Graph now supports mechanical retries (no AI yet)

**Edge Logic**:
- ✅ `should_continue()` function returns typed EdgeDecision ("end_success" | "end_failure" | "retry")
- ✅ Success check: All validators passed → end_success
- ✅ Max attempts check: attempt >= max_attempts - 1 → end_failure
- ✅ Otherwise → retry (continue loop)
- ✅ Clean separation of routing logic from node logic

**Failure History Tracking**:
- ✅ Moved from `increment_attempt_node` to `validate_node`
- ✅ Ensures ALL validation attempts are recorded (including the last one)
- ✅ Each history entry is a list of ValidationResults
- ✅ History accumulates across all retry iterations
- ✅ Ready for STEP 5 (AI will use history to understand patterns)

**Attempt Counter**:
- ✅ Increments after each validation failure
- ✅ 0-indexed (attempt 0, 1, 2 = 3 total attempts)
- ✅ Checked against max_attempts in should_continue()
- ✅ Preserved across state updates
- ✅ Displayed in increment_attempt_node progress messages

**Test Coverage**:
- ✅ `tests/unit/test_graph.py`: Added 9 new retry loop tests
  1. Success on first attempt goes directly to END (no retry)
  2. Failure with attempts remaining increments attempt counter
  3. Max attempts reached goes to END with failure
  4. Failure history tracked correctly across attempts
  5. Attempt counter increments correctly (0 → 1 → 2 → ...)
  6. Graph executes multiple retry loops (3, 4, 5 attempts)
  7. State preserved across iterations (env_vars, working_dir, etc.)
  8. should_continue() edge function routing (3 cases tested)
  9. Integration test with real failing validator

**Test Results**:
- 126 tests passing (9 new retry loop tests + 117 existing)
- 94.56% code coverage (exceeds 90% target)
- 100% coverage on edges.py (new file)
- 100% coverage on builder.py (updated file)
- 87.59% coverage on nodes.py (validate_node + increment_attempt_node)
- Mypy strict passing on all 17 source files
- All tests complete in <3 seconds
- Graph successfully loops on validation failures

**Behavioral Changes**:
- ✅ **Before STEP 3**: Graph was linear (START → pre_actions → validate → decide → END)
- ✅ **After STEP 3**: Graph loops on failure (validate → decide → increment_attempt → validate)
- ✅ **Mechanical retries**: Validators fail → retry → validators fail again (no fixing yet)
- ✅ **Max attempts enforcement**: Stops after max_attempts iterations
- ✅ **Exit paths**: 2 ways to END (success or max_attempts reached)

**Example Retry Loop Flow**:
```
Attempt 0: validate → fail → decide → retry → increment_attempt
Attempt 1: validate → fail → decide → retry → increment_attempt
Attempt 2: validate → fail → decide → end_failure (max_attempts=3)

Result: success=False, attempt=2, failure_history=[attempt0, attempt1, attempt2]
```

**Key Architectural Note**:
- **CRITICAL**: This step does NOT add AI fixing. The retry loop is purely mechanical.
- Validators fail → increment attempt → run validators again → fail again
- This will loop until max_attempts without actually fixing anything
- **Purpose**: Prove the graph can loop correctly, enforce max attempts, track history
- **STEP 5 will add**: ai_fix_node that slots into the retry path to actually fix issues

**Future Flow** (after STEP 5):
```
validate → decide
    ├─ success → END
    ├─ max_attempts → END (failure)
    └─ retry → ai_fix → increment_attempt → validate
               ^^^^^^^^^^^
            (Added in STEP 5 - Claude fixes issues)
```

**Ready For**: STEP 4 - AI Tools (NOT Validators) for Investigation & Fixing

---

### **STEP 4: Claude Code Agent SDK Integration**

**Goal**: Integrate Claude Code Agent SDK for AI-assisted investigation and fixing using built-in tools

**CRITICAL CHANGE**: We do NOT create custom tools! Claude Code Agent SDK provides powerful built-in tools that handle all investigation and fixing needs.

**Key Insight**:
- **Before**: Planned to create 9 custom @tool decorated functions
- **After**: Use SDK's 5 built-in tools (Bash, Read, Edit, Grep, Glob)
- **Why**: SDK's Bash tool can execute ANY shell command (git, gh, make, etc.), making custom wrappers unnecessary

**SDK Built-in Tools Available**:
1. **Bash**: Execute any shell command - covers git operations, gh commands, system tools
2. **Read**: Read file contents with optional line ranges
3. **Edit**: Edit files by replacing old_string with new_string
4. **Grep**: Advanced regex search with multiple output modes
5. **Glob**: Find files matching patterns

**Deliverables**:
- ✅ Claude Agent SDK client wrapper (ConvergenceAgent class)
- ✅ System prompt builder (explains validation failures to Claude)
- ✅ User message builder (provides current failure details)
- ✅ SDK configuration (allowed_tools, permission_mode, working_directory)
- ✅ Async integration for LangGraph ai_fix_node

**Files to Create**:
- `src/alphanso/agent/__init__.py` - Package initialization
- `src/alphanso/agent/client.py` - SDK wrapper and ConvergenceAgent class
- `src/alphanso/agent/prompts.py` - Prompt builders
- `tests/unit/test_agent_client.py` - Unit tests for client wrapper
- `tests/integration/test_claude_sdk.py` - Integration tests with real SDK

**Claude Agent SDK Client Wrapper**:
```python
# src/alphanso/agent/client.py
from anthropic import Anthropic
from typing import Any, Dict, List, Optional
import os

class ConvergenceAgent:
    """Wrapper around Claude Code Agent SDK for convergence loop.

    This class provides a simple interface to invoke Claude with the SDK's
    built-in tools (Bash, Read, Edit, Grep, Glob) for investigation and fixing.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 8192,
        working_directory: Optional[str] = None,
    ):
        """Initialize Claude Agent SDK client.

        Args:
            model: Claude model to use
            max_tokens: Max tokens for responses
            working_directory: Working directory for commands (optional)
        """
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model
        self.max_tokens = max_tokens
        self.working_directory = working_directory or os.getcwd()

    async def invoke(
        self,
        system_prompt: str,
        user_message: str,
        allowed_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Invoke Claude with validation failure context.

        Claude will use SDK's built-in tools to investigate and fix:
        - Bash: Execute any command (git, gh, make, etc.)
        - Read: Read file contents
        - Edit: Edit files by replacing content
        - Grep: Search code
        - Glob: Find files

        Args:
            system_prompt: Explains validation failures and available tools
            user_message: Current validation results
            allowed_tools: List of SDK tools to enable (default: all)

        Returns:
            Response dict with content and tool_calls
        """
        # Default to all SDK built-in tools
        if allowed_tools is None:
            allowed_tools = ["bash", "read", "edit", "grep", "glob"]

        # Create messages
        messages = [
            {"role": "user", "content": user_message}
        ]

        # Invoke Claude Code Agent SDK
        # SDK automatically provides the built-in tools
        response = await self.client.messages.create_async(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=messages,
            # SDK-specific options for tool access
            tools=[{"type": t} for t in allowed_tools],
            # Pass working directory for Bash tool
            tool_choice={"type": "auto"},
        )

        # Extract tool calls from response
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "tool": block.name,
                    "input": block.input,
                    "output": getattr(block, "output", None),
                })

        return {
            "content": response.content,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason,
        }
```

**Prompt Builder** (explains validation failures to Claude):
```python
# src/alphanso/agent/prompts.py
from alphanso.graph.state import ConvergenceState

def build_fix_prompt(state: ConvergenceState) -> str:
    """Build system prompt for AI fix node.

    Explains to Claude:
    - What validators failed (run by framework, not Claude)
    - What SDK tools are available for investigation
    - How to use Bash tool for git, gh, make, etc.
    """
    attempt = state["attempt"]
    max_attempts = state["max_attempts"]
    failed = state["failed_validators"]

    prompt = f"""You are helping fix validation failures in a convergence loop.

Attempt: {attempt + 1}/{max_attempts}

IMPORTANT: You have access to investigation and fixing tools from Claude Code Agent SDK.
The framework runs validators (make, make test, etc.) and reports results to you.
Your job is to investigate WHY they failed and FIX the issues.

Failed Validators (run by framework, not you):
{', '.join(failed)}

Available SDK Tools:
- **Bash**: Execute ANY shell command
  - git status, git diff, git blame, git log
  - gh pr list, gh pr view
  - make, make test, go test, etc.
  - grep, find, cat, etc.
- **Read**: Read file contents (with optional line ranges)
- **Edit**: Edit files by replacing old_string with new_string
- **Grep**: Advanced regex search (multiple output modes)
- **Glob**: Find files matching patterns (e.g., "**/*.go")

Investigation workflow:
1. Read validation failure output (provided below)
2. Use Bash tool: git blame, git log to understand context
3. Use Bash tool: gh pr list, gh pr view to find related changes
4. Use Read tool to understand code
5. Use Edit tool to apply fixes
6. The framework will re-run validators after you're done

Previous attempts:
"""

    # Add failure history
    for i, history in enumerate(state["failure_history"]):
        prompt += f"\nAttempt {i + 1}:\n"
        for result in history:
            if not result["success"]:
                prompt += f"  - {result['validator_name']}: {result['output'][:200]}\n"

    return prompt


def build_user_message(state: ConvergenceState) -> str:
    """Build user message with current failure details."""

    message = "The framework ran validators and the following failed:\n\n"

    for result in state["validation_results"]:
        if not result["success"]:
            message += f"## Validator: {result['validator_name']}\n"
            message += f"Exit Code: {result['exit_code']}\n"
            message += f"Output:\n```\n{result['output']}\n```\n"
            if result["stderr"]:
                message += f"Stderr:\n```\n{result['stderr']}\n```\n"

            # Include metadata (e.g., failing packages)
            if result.get("metadata"):
                message += f"Metadata: {result['metadata']}\n"

            message += "\n"

    message += "Please investigate using SDK tools and fix the issues."

    return message
```

**SDK Configuration Example**:
```python
# Example: Configure agent with SDK tools in config file
agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"
    max_tokens: 8192

  # SDK built-in tools to enable
  allowed_tools:
    - bash   # Execute any command (git, gh, make, etc.)
    - read   # Read files
    - edit   # Edit files
    - grep   # Search code
    - glob   # Find files

  # Permission mode for SDK
  permission_mode: "auto"  # or "ask_user" for manual approval
```

**Test Cases**:
1. ConvergenceAgent wrapper initializes correctly
2. System prompt explains validators and SDK tools
3. User message includes validation results
4. SDK's Bash tool can be invoked (git, gh commands)
5. SDK's Read tool can read files
6. SDK's Edit tool can edit files
7. SDK's Grep tool can search code
8. SDK's Glob tool can find files
9. Agent response captures tool calls
10. Working directory is passed to SDK

**Success Criteria**:
- ✅ All 10 test cases pass
- ✅ Claude uses SDK built-in tools, not custom tools
- ✅ Bash tool covers all git/gh/system commands
- ✅ Type checking passes
- ✅ Code coverage ≥ 85%
- ✅ SDK integration is simple and maintainable

---

### **STEP 5: AI Fix Node Integration**

**Goal**: Add `ai_fix_node` to graph to invoke Claude Agent SDK (from STEP 4)

**IMPORTANT**: STEP 4 already created ConvergenceAgent wrapper and prompt builders. STEP 5 just integrates them into the graph's retry loop.

**Deliverables**:
- ✅ `ai_fix_node` - Graph node that invokes ConvergenceAgent
- ✅ Update graph builder to add ai_fix_node to retry path
- ✅ Integration tests showing full loop: validate → ai_fix → validate
- ✅ State tracking for agent tool calls and messages

**Files to Modify**:
- `src/alphanso/graph/nodes.py` - Add ai_fix_node
- `src/alphanso/graph/builder.py` - Add ai_fix to graph, route retry through it
- `tests/unit/test_graph.py` - Test ai_fix_node integration
- `tests/integration/test_full_loop.py` - End-to-end test with real Claude

**AI Fix Node Implementation**:
```python
# src/alphanso/graph/nodes.py
from alphanso.agent.client import ConvergenceAgent
from alphanso.agent.prompts import build_fix_prompt, build_user_message

async def ai_fix_node(state: ConvergenceState) -> dict[str, Any]:
    """Invoke Claude Agent SDK to fix validation failures.

    This node:
    1. Uses prompt builders from STEP 4 to explain failures
    2. Invokes ConvergenceAgent with SDK built-in tools
    3. Tracks tool calls and messages in state
    4. Returns to increment_attempt → validate

    Claude uses SDK tools (Bash, Read, Edit, Grep, Glob) to:
    - Investigate failures using git commands (via Bash tool)
    - Read and edit files to fix issues
    - Search code to understand context

    NOTE: Claude does NOT run validators. Framework runs them.
    """
    print("\n" + "=" * 70)
    print("NODE: ai_fix")
    print("=" * 70)
    print("Invoking Claude Agent SDK to investigate and fix failures...")
    print()

    # Build prompts (from STEP 4)
    system_prompt = build_fix_prompt(state)
    user_message = build_user_message(state)

    # Initialize agent (from STEP 4)
    agent = ConvergenceAgent(
        model=state.get("agent_config", {}).get("model", "claude-sonnet-4-5-20250929"),
        max_tokens=state.get("agent_config", {}).get("max_tokens", 8192),
        working_directory=state.get("working_directory"),
    )

    # Invoke Claude with SDK built-in tools
    # SDK provides: Bash, Read, Edit, Grep, Glob
    response = await agent.invoke(
        system_prompt=system_prompt,
        user_message=user_message,
        allowed_tools=state.get("agent_config", {}).get("allowed_tools"),
    )

    # Track what Claude did
    tool_calls = response.get("tool_calls", [])

    print(f"✅ Claude used {len(tool_calls)} SDK tools")
    for call in tool_calls:
        print(f"   - {call['tool']}: {call.get('input', {})}")
    print()

    # Return state updates
    return {
        "agent_tool_calls": [
            *state.get("agent_tool_calls", []),
            *tool_calls
        ],
        "agent_messages": [
            *state.get("agent_messages", []),
            str(response["content"])
        ],
    }
```

**Updated Graph with AI Fix Node**:
```python
# src/alphanso/graph/builder.py
def create_convergence_graph() -> ConvergenceGraph:
    """Create convergence graph with AI fix node in retry loop.

    Flow with STEP 5:

    START → pre_actions → validate → decide → {end_success, end_failure, retry}
                            ↑                           │
                            └─ increment_attempt ← ai_fix ←┘

    When validation fails and attempts remain:
    1. decide → "retry" → ai_fix (Claude investigates and fixes)
    2. ai_fix → increment_attempt (track iteration)
    3. increment_attempt → validate (re-run validators)
    """
    graph = StateGraph(ConvergenceState)

    # Add nodes
    graph.add_node("pre_actions", pre_actions_node)
    graph.add_node("validate", validate_node)
    graph.add_node("decide", decide_node)
    graph.add_node("ai_fix", ai_fix_node)  # NEW: STEP 5
    graph.add_node("increment_attempt", increment_attempt_node)

    # Linear edges (setup phase)
    graph.add_edge(START, "pre_actions")
    graph.add_edge("pre_actions", "validate")
    graph.add_edge("validate", "decide")

    # Conditional edges (retry logic with AI)
    graph.add_conditional_edges(
        "decide",
        should_continue,
        {
            "end_success": END,
            "end_failure": END,
            "retry": "ai_fix",  # CHANGED: Route through AI fix
        },
    )

    # Retry loop edges (STEP 5: AI fixes, then retry)
    graph.add_edge("ai_fix", "increment_attempt")
    graph.add_edge("increment_attempt", "validate")

    return graph.compile()
```

**Test Cases**:
1. ai_fix_node invokes ConvergenceAgent correctly
2. System prompt built from build_fix_prompt()
3. User message built from build_user_message()
4. Agent SDK built-in tools are available (Bash, Read, Edit, Grep, Glob)
5. Bash tool can execute git commands
6. Read/Edit tools can modify files
7. Tool calls are tracked in state
8. Graph flow: validate → decide → ai_fix → increment → validate
9. Integration test with real Claude SDK
10. Agent does NOT have access to validators (separation maintained)

**Success Criteria**:
- ✅ All 10 test cases pass
- ✅ Claude uses SDK built-in tools from STEP 4
- ✅ Flow is correct: framework validates, Claude fixes (using SDK), framework re-validates
- ✅ Type checking passes
- ✅ Code coverage ≥ 85%
- ✅ ai_fix_node slots cleanly into retry loop

---

### **STEP 6: Configuration System**

(Configuration remains largely the same, but clarify validator vs AI tool config)

```yaml
# Example config - Kubernetes Rebase
name: "Kubernetes Rebase"
max_attempts: 100

# Pre-actions - Run ONCE before convergence loop
pre_actions:
  - command: "git fetch upstream"
    description: "Fetch upstream changes"

  - command: "git merge upstream/${K8S_TAG}"
    description: "Merge upstream Kubernetes tag"

  - command: "./kubernetes/openshift-hack/lib/ci-image-setup.sh"
    description: "Setup CI container"

  - command: "go mod tidy"
    description: "Tidy Go modules"

# Validators - CONDITIONS we check (run by framework in loop)
validators:
  - type: git-conflict
    name: "Git Conflict Check"
    timeout: 10

  - type: container-command
    name: "Container Operations"
    container: "ci-image"
    commands:
      - "source hack/install-etcd.sh"
      - "hack/update-vendor.sh"
      - "make update"
    timeout: 900

  - type: command
    name: "Build"
    command: "make"
    timeout: 600

  - type: test-suite
    name: "Tests"
    command: "make test"
    timeout: 1800

# Agent configuration - Claude Code Agent SDK
agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"
    max_tokens: 8192

  # SDK built-in tools (Bash covers all git/gh/system commands)
  allowed_tools:
    - bash   # Execute any command (git, gh, make, grep, find, etc.)
    - read   # Read file contents
    - edit   # Edit files
    - grep   # Search code
    - glob   # Find files

retry_strategy:
  type: hybrid
  max_tracked_failures: 10
```

---

### **STEP 7: Container Operations Validator**

**Goal**: Support running validators inside containers (critical for Kubernetes rebase)

**Deliverables**:
- `ContainerCommandValidator` for running commands in containers
- Support for podman/docker
- Multi-command sequences with failure handling
- Output capture and logging
- Integration with CI container setup

**Files to Create**:
- `src/alphanso/validators/container.py`
- `tests/unit/test_container_validator.py`
- `tests/integration/test_container_operations.py`

**Container Command Validator**:
```python
import subprocess
from typing import List, Optional

class ContainerCommandValidator(Validator):
    """
    Run commands inside a container.

    Critical for Kubernetes rebase where make update, vendor updates,
    etc. must run in the CI container environment.
    """

    def __init__(
        self,
        name: str,
        container: str,
        commands: List[str],
        timeout: float = 900.0,
        runtime: str = "podman"  # or "docker"
    ):
        super().__init__(name, timeout)
        self.container = container
        self.commands = commands
        self.runtime = runtime

    def validate(self) -> ValidationResult:
        """Run commands in container sequentially."""

        all_output = []
        all_stderr = []

        for cmd in self.commands:
            # Run in container
            container_cmd = f"{self.runtime} exec {self.container} bash -c '{cmd}'"

            result = subprocess.run(
                container_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            all_output.append(f"$ {cmd}\n{result.stdout}")
            if result.stderr:
                all_stderr.append(result.stderr)

            # Stop on first failure
            if result.returncode != 0:
                return ValidationResult(
                    validator_name=self.name,
                    success=False,
                    output='\n'.join(all_output)[-2000:],
                    stderr='\n'.join(all_stderr)[-1000:],
                    exit_code=result.returncode,
                    duration=0.0,
                    timestamp=0.0,
                    metadata={"failed_command": cmd}
                )

        # All succeeded
        return ValidationResult(
            validator_name=self.name,
            success=True,
            output='\n'.join(all_output)[-2000:],
            stderr='',
            exit_code=0,
            duration=0.0,
            timestamp=0.0,
            metadata={"commands_run": len(self.commands)}
        )
```

**Configuration Example**:
```yaml
validators:
  - type: container-command
    name: "Container Operations"
    container: "ci-image"
    runtime: "podman"
    commands:
      - "go mod tidy"
      - "source hack/install-etcd.sh"
      - "hack/update-vendor.sh"
      - "make update"
    timeout: 900
```

**Test Cases**:
1. Runs single command in container successfully
2. Runs multiple commands in sequence
3. Stops on first failure
4. Captures output from all commands
5. Works with both podman and docker
6. Handles container not found error
7. Respects timeout
8. Metadata includes failed command
9. Output is properly truncated
10. Integration test with real container

**Success Criteria**:
- ✅ All 10 test cases pass
- ✅ Integration test with real container passes
- ✅ Type checking passes
- ✅ Code coverage ≥ 90%

---

### **STEP 8: Targeted Retry Strategy**

**Goal**: Smart retry that only re-runs failed tests/validators (efficiency optimization)

**Deliverables**:
- Retry strategy abstraction
- `HybridRetryStrategy` - targeted first, then full
- Integration with TestSuiteValidator
- Failure extraction from test output
- Configuration support

**Files to Create**:
- `src/alphanso/graph/retry_strategy.py`
- Update `src/alphanso/validators/test_suite.py`
- `tests/unit/test_retry_strategy.py`

**Retry Strategy Interface**:
```python
from abc import ABC, abstractmethod
from typing import List

class RetryStrategy(ABC):
    """Base class for retry strategies."""

    @abstractmethod
    def should_run_targeted(
        self,
        attempt: int,
        validator_config: Dict,
        previous_failures: List[str]
    ) -> bool:
        """Determine if should run targeted retry."""
        pass

class HybridRetryStrategy(RetryStrategy):
    """
    Run targeted retry first (only known failures), then full validation.

    Efficiency: If 5/100 tests fail, retry just those 5, then run full 100.
    """

    def __init__(self, max_tracked_failures: int = 10):
        self.max_tracked_failures = max_tracked_failures

    def should_run_targeted(
        self,
        attempt: int,
        validator_config: Dict,
        previous_failures: List[str]
    ) -> bool:
        """Run targeted if we have trackable failures."""
        return (
            attempt > 0 and  # Not first attempt
            len(previous_failures) > 0 and  # Have known failures
            len(previous_failures) <= self.max_tracked_failures and  # Not too many
            validator_config.get("type") == "test-suite"  # Supports targeted
        )
```

**Enhanced TestSuiteValidator**:
```python
import re
from typing import List, Optional, Dict

class TestSuiteValidator(Validator):
    """Run tests with intelligent failure extraction and targeted retry."""

    def __init__(
        self,
        name: str,
        command: str,
        framework: str = "go-test",  # or "pytest", "jest"
        timeout: float = 1800.0,
        targeted_packages: Optional[List[str]] = None
    ):
        super().__init__(name, timeout)
        self.command = command
        self.framework = framework
        self.targeted_packages = targeted_packages
        self.failure_patterns = self._get_failure_patterns()

    def _get_failure_patterns(self) -> Dict[str, str]:
        """Regex patterns for extracting failures by framework."""
        return {
            "go-test": r'^FAIL\s+(\S+)',
            "pytest": r'^FAILED\s+(\S+)',
            "jest": r'^\s*●\s+(.+)',
        }

    def validate(self) -> ValidationResult:
        """Run tests and extract failures."""

        # Build command (targeted or full)
        if self.targeted_packages and self.framework == "go-test":
            cmd = f"go test {' '.join(self.targeted_packages)}"
        else:
            cmd = self.command

        # Run tests
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )

        # Extract failures
        failing = []
        if result.returncode != 0:
            pattern = self.failure_patterns.get(self.framework)
            if pattern:
                for line in result.stdout.split('\n'):
                    match = re.match(pattern, line)
                    if match:
                        failing.append(match.group(1))

        # Build output with failure summary
        output = result.stdout[-2000:]  # Last 2000 chars
        if failing:
            output += f"\n\nFailing packages/tests ({len(failing)}):\n"
            output += "\n".join(f"  - {f}" for f in failing[:10])

        return ValidationResult(
            validator_name=self.name,
            success=result.returncode == 0,
            output=output,
            stderr=result.stderr[-1000:],
            exit_code=result.returncode,
            duration=0.0,
            timestamp=0.0,
            metadata={"failing_packages": failing[:10]}  # Store for retry
        )
```

**Updated Validate Node** (with retry strategy):
```python
def validate_node(state: ConvergenceState) -> ConvergenceState:
    """Execute validators with retry strategy."""

    results = []
    failed = []

    # Get retry strategy
    strategy = get_retry_strategy(state["retry_strategy"])

    for validator_config in state["validators_config"]:
        validator = create_validator(validator_config)

        # Get previous failures for this validator
        previous_failures = get_previous_failures(
            state["failure_history"],
            validator.name
        )

        # Apply targeted retry strategy
        if strategy.should_run_targeted(
            state["attempt"],
            validator_config,
            previous_failures
        ):
            # Targeted retry
            if isinstance(validator, TestSuiteValidator):
                validator.targeted_packages = previous_failures

        # Run validator
        result = validator.run()
        results.append(result)

        if not result["success"]:
            failed.append(result["validator_name"])

        # If targeted passed, run full validation
        if (
            validator.targeted_packages and
            result["success"] and
            strategy.run_full_after_targeted
        ):
            validator.targeted_packages = None
            full_result = validator.run()
            results.append({**full_result, "validator_name": f"{validator.name} (full)"})
            if not full_result["success"]:
                failed.append(full_result["validator_name"])

    return {
        **state,
        "validation_results": results,
        "failed_validators": failed,
        "success": len(failed) == 0
    }
```

**Example Behavior**:
```
Attempt 1: Run full test suite (100 tests)
  → 5 tests fail: pkg/foo, pkg/bar, pkg/baz, pkg/qux, pkg/quux

Attempt 2 (after AI fixes): Run targeted (5 tests)
  → 2 tests still fail: pkg/bar, pkg/qux

Attempt 3 (after AI fixes): Run targeted (2 tests)
  → All pass! ✓
  → Run full suite to catch regressions (100 tests)
  → All pass! ✓ SUCCESS
```

**Test Cases**:
1. First attempt runs full validation
2. Retry runs targeted validation for known failures
3. After targeted success, full validation runs
4. Max failures limit is respected
5. Strategy selection from config works
6. Targeted retry saves time (measurable)
7. Failure extraction works for go-test
8. Failure extraction works for pytest
9. Statistics track targeted vs full runs
10. Edge cases (0 failures, too many failures)

**Success Criteria**:
- ✅ All 10 test cases pass
- ✅ Efficiency improvement measurable (≥50% time saved)
- ✅ Type checking passes
- ✅ Code coverage ≥ 90%

---

### **STEP 9: CLI Interface**

**Goal**: User-friendly command-line interface with rich output

**Deliverables**:
- Click-based CLI with subcommands
- `ai-convergence run` - run convergence loop
- `ai-convergence validate` - validate config
- `ai-convergence init` - create starter config
- Rich progress output with colors
- JSON output mode for CI
- Variable substitution support

**Files to Create**:
- `src/alphanso/cli.py`
- `src/alphanso/__main__.py`
- `src/alphanso/utils/output.py`
- `tests/unit/test_cli.py`
- Update `pyproject.toml` with console_scripts

**CLI Structure**:
```python
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import json
import os

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Alphanso - Iterative problem solving with AI."""
    pass

@cli.command()
@click.option("--config", "-c", required=True, help="Configuration YAML file")
@click.option("--var", "-v", multiple=True, help="Variable override (KEY=VALUE)")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--no-color", is_flag=True, help="Disable color output")
def run(config: str, var: tuple, verbose: bool, json_output: bool, no_color: bool):
    """Run convergence loop with configuration."""

    if no_color:
        console = Console(no_color=True)

    # Parse variables
    vars_dict = {}
    for v in var:
        key, value = v.split("=", 1)
        vars_dict[key] = value
        os.environ[key] = value

    # Load config
    try:
        cfg = ConvergenceConfig.from_yaml(config)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        raise click.Abort()

    # Create and run graph
    if not json_output:
        console.print(f"[bold]Alphanso[/bold] v0.1.0\n")
        console.print(f"Config: {config}")
        console.print(f"Max Attempts: {cfg.max_attempts}")
        console.print(f"Validators: {len(cfg.validators)}\n")

    graph = create_convergence_graph(cfg)
    initial_state = create_initial_state(cfg)

    # Run with progress
    if json_output:
        final_state = graph.invoke(initial_state)
        output_json(final_state)
    else:
        final_state = run_with_progress(graph, initial_state, verbose)
        output_results(final_state)

    # Exit code
    sys.exit(0 if final_state["success"] else 1)

@cli.command()
@click.option("--config", "-c", required=True, help="Configuration YAML file")
def validate(config: str):
    """Validate configuration file."""
    try:
        cfg = ConvergenceConfig.from_yaml(config)
        console.print(f"[green]✓[/green] Configuration is valid")

        # Show summary
        table = Table(title="Configuration Summary")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Name", cfg.name)
        table.add_row("Max Attempts", str(cfg.max_attempts))
        table.add_row("Validators", str(len(cfg.validators)))
        table.add_row("Model", cfg.agent.model)

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Configuration is invalid:[/red] {e}")
        sys.exit(1)

@cli.command()
@click.option("--template", "-t", type=click.Choice(["simple", "kubernetes"]), default="simple")
def init(template: str):
    """Generate starter configuration."""
    templates = {
        "simple": """name: "My Alphanso Loop"
max_attempts: 10

agent:
  model: "claude-sonnet-4-5-20250929"

validators:
  - type: command
    name: "Build"
    command: "make"

  - type: command
    name: "Test"
    command: "make test"

retry_strategy:
  type: hybrid
""",
        "kubernetes": """# Kubernetes rebase configuration
# ... (full template)
"""
    }

    console.print(templates[template])
```

**Progress Display**:
```python
def run_with_progress(graph, initial_state, verbose):
    """Run graph with rich progress display."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        for state in graph.stream(initial_state):
            attempt = state["attempt"]

            # Show validation results
            if state.get("validation_results"):
                console.print(f"\n[bold]Attempt {attempt + 1}[/bold]")

                for result in state["validation_results"]:
                    status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
                    duration = f"({result['duration']:.1f}s)"
                    console.print(f"{status} {result['validator_name']} {duration}")

                    if verbose and not result["success"]:
                        console.print(f"  [dim]{result['output'][:200]}[/dim]")

            # Show AI activity
            if state.get("agent_messages"):
                console.print("🤖 [cyan]AI assistant working...[/cyan]")

        return state
```

**CLI Examples**:
```bash
# Run with config
alphanso run --config rebase.yaml

# With variables
alphanso run --config rebase.yaml \
  --var K8S_TAG=v1.35.0 \
  --var OPENSHIFT_RELEASE=release-4.22

# Verbose mode
alphanso run --config rebase.yaml --verbose

# JSON output for CI
alphanso run --config rebase.yaml --json > result.json

# Validate config
alphanso validate --config rebase.yaml

# Create starter config
alphanso init --template simple > my-config.yaml
```

**Test Cases**:
1. CLI loads and runs config
2. CLI handles missing config file gracefully
3. CLI variable substitution works
4. CLI exit codes are correct (0=success, 1=failure)
5. `--help` shows usage for all commands
6. `--verbose` increases output detail
7. `--json` outputs structured JSON
8. `validate` command catches invalid configs
9. `init` command creates valid starter config
10. Progress display works
11. Color output can be disabled
12. Rich formatting works correctly

**Success Criteria**:
- ✅ All 12 test cases pass
- ✅ CLI is intuitive and well-documented
- ✅ Output is beautiful and informative
- ✅ JSON mode enables CI integration
- ✅ Code coverage ≥ 85%

---

### **STEP 10: Example - Dependency Upgrade**

**Goal**: Demonstrate framework with realistic example (simpler than Kubernetes)

**Deliverables**:
- Complete example: Go module upgrade
- Sample Go project with intentional API breakage
- Configuration file
- Documentation with before/after
- Runnable demo

**Files to Create**:
- `examples/03_dependency_upgrade/config.yaml`
- `examples/03_dependency_upgrade/README.md`
- `examples/03_dependency_upgrade/sample_project/` (Go app)
- `examples/03_dependency_upgrade/run.sh`

**Example Config**:
```yaml
name: "Go Dependency Upgrade"
max_attempts: 5

agent:
  model: "claude-sonnet-4-5-20250929"
  max_tokens: 4096

# Pre-actions - upgrade the dependency
pre_actions:
  - command: "go get -u github.com/some/module@v2.0.0"
    description: "Update dependency to v2.0.0"

validators:
  - type: command
    name: "Go Mod Tidy"
    command: "go mod tidy"
    timeout: 60

  - type: command
    name: "Build"
    command: "go build ./..."
    timeout: 300

  - type: test-suite
    name: "Tests"
    command: "go test ./..."
    framework: go-test
    retry_strategy:
      type: hybrid

# Agent configuration - Claude Code Agent SDK
agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"
    max_tokens: 4096

  # SDK built-in tools
  allowed_tools:
    - bash   # Covers git commands
    - read
    - edit
    - grep
    - glob

retry_strategy:
  type: hybrid
```

**Sample Project** (with intentional API breakage):
```go
// sample_project/main.go
package main

import (
    "github.com/some/module/v1"  // Will upgrade to v2
)

func main() {
    // This will break after upgrade
    result := module.OldAPI()  // v2 uses NewAPI()
    println(result)
}
```

**Test Cases**:
1. Example runs end-to-end successfully
2. AI fixes API breakage correctly
3. Documentation is clear and complete
4. Example demonstrates value (manual vs automated)
5. Example can be run by users without modification

**Documentation Sections**:
- **Problem**: "Upgrading dependencies is tedious and error-prone"
- **Solution**: "Automate with AI Convergence Framework"
- **Before**: Manual process (8 steps, 30+ minutes)
- **After**: Automated process (1 command, 5 minutes)
- **How it works**: Step-by-step explanation
- **Try it yourself**: Instructions to run example

**Success Criteria**:
- ✅ Example runs successfully in fresh checkout
- ✅ Documentation is clear and compelling
- ✅ Demonstrates clear value over manual process
- ✅ Can serve as template for similar use cases

---

### **STEP 11: Kubernetes Rebase Integration**

**Goal**: Port rebase.sh to framework (primary use case)

**Deliverables**:
- Complete config for Kubernetes rebase
- Custom validators for OpenShift
- Bash wrapper for backwards compatibility
- Migration guide
- End-to-end testing

**Files to Create**:
- `examples/04_kubernetes_rebase/config.yaml`
- `examples/04_kubernetes_rebase/rebase.sh`
- `examples/04_kubernetes_rebase/README.md`
- `examples/04_kubernetes_rebase/MIGRATION.md`
- `tests/e2e/test_kubernetes_rebase.py`

**Example Config**:
```yaml
name: "Kubernetes Rebase for OpenShift"
max_attempts: 100
timeout: 7200  # 2 hours

agent:
  model: "claude-sonnet-4-5-20250929"
  max_tokens: 8192

# Pre-actions - Run ONCE before convergence loop
pre_actions:
  - command: "git fetch upstream"
    description: "Fetch upstream changes"

  - command: "git merge upstream/${K8S_TAG}"
    description: "Merge upstream Kubernetes tag"

  - command: "./kubernetes/openshift-hack/lib/ci-image-setup.sh"
    description: "Setup CI container"

  - command: "go mod tidy"
    description: "Tidy Go modules"

# Validators - CONDITIONS checked by framework
validators:
  - type: git-conflict
    name: "Git Conflict Check"
    timeout: 10

  - type: container-command
    name: "Container Operations"
    container: "ci-image"
    commands:
      - "source hack/install-etcd.sh"
      - "hack/update-vendor.sh"
      - "make update"
    timeout: 900

  - type: command
    name: "Build"
    command: "make"
    timeout: 600

  - type: test-suite
    name: "Tests"
    command: "make test"
    framework: go-test
    timeout: 1800
    retry_strategy:
      type: hybrid
      max_tracked_failures: 10

# Agent configuration - Claude Code Agent SDK
agent:
  type: "claude-agent-sdk"
  claude:
    model: "claude-sonnet-4-5-20250929"
    max_tokens: 8192

  # SDK built-in tools (Bash covers all git/gh commands)
  allowed_tools:
    - bash   # Execute ANY command (git, gh, make, etc.)
    - read   # Read file contents
    - edit   # Edit files
    - grep   # Search code
    - glob   # Find files matching patterns

retry_strategy:
  type: hybrid
  max_tracked_failures: 10

graph:
  checkpointing: true  # Enable for long-running rebases

env_vars:
  K8S_TAG: "${K8S_TAG}"
  OPENSHIFT_RELEASE: "${OPENSHIFT_RELEASE}"
  KUBE_REPO: "${PWD}"
```

**Bash Wrapper** (`rebase.sh`):
```bash
#!/bin/bash
set -euo pipefail

# Backwards compatible interface
k8s_tag="$1"
openshift_release="$2"

# Source existing lib files for container setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../lib/ci-image-setup.sh"

# Setup CI container (existing logic)
setup_ci_image

# Run framework
alphanso run \
  --config "${SCRIPT_DIR}/config.yaml" \
  --var K8S_TAG="$k8s_tag" \
  --var OPENSHIFT_RELEASE="$openshift_release" \
  --var KUBE_REPO="$(pwd)" \
  --verbose
```

**Test Cases**:
1. Rebase handles clean merge (no conflicts)
2. Rebase handles merge conflicts
3. Container operations work correctly
4. make/make test work correctly
5. Retry logic matches old behavior
6. OpenShift changes preserved
7. Performance is comparable
8. End-to-end with real Kubernetes tags
9. Migration successful
10. Team approval

**Success Criteria**:
- ✅ Successfully rebases Kubernetes
- ✅ Performance within 10% of bash version
- ✅ All features migrated
- ✅ Team approves migration

---

### **STEP 12: Documentation & Polish**

**Goal**: Production-ready documentation

**Deliverables**:
- Comprehensive README
- API documentation
- Architecture guide
- Contributing guide
- Examples for all use cases

**Files to Create**:
- `README.md`
- `docs/architecture.md`
- `docs/writing-validators.md`
- `docs/configuration.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`

**README Sections**:
1. **Hero Section**: What is this? Why use it?
2. **Quickstart**: Get started in 5 minutes
3. **Installation**: `pip install alphanso` or `uv add alphanso`
4. **Key Concepts**: State graph, validators, AI tools
5. **Examples**: Links to 4+ examples
6. **Configuration**: Brief overview
7. **Use Cases**: When to use this framework
8. **Architecture**: High-level diagram
9. **Contributing**: Link to CONTRIBUTING.md
10. **License**: Link to LICENSE
11. **Acknowledgments**: Inspired by rebaser project

**Writing Validators Guide Outline**:
1. Validator interface overview
2. Simple validator example
3. Advanced validator example (test suite)
4. Testing your validator
5. Configuration integration
6. Best practices

**Configuration Reference**:
- Every config option documented
- Type information
- Default values
- Examples for each option
- Validation rules

**Success Criteria**:
- ✅ New user can get started in 15 min
- ✅ All APIs documented
- ✅ Examples cover common use cases
- ✅ Ready for external users

---

## Summary of Corrected Architecture

### **What Changed:**

1. **Validators are NOT tools for Claude**
   - Validators run in `validate_node` by the framework
   - Results are passed to Claude as context
   - Claude never runs `make` or `make test`

2. **Claude gets investigation/fixing tools**
   - `git` commands (diff, blame, log, status)
   - `gh` commands (pr view, pr list)
   - File operations (read, edit, search)
   - These help Claude understand and fix issues

3. **Clear flow:**
   ```
   Framework runs validators
        ↓
   Validators fail → Send failure details to Claude
        ↓
   Claude uses AI tools to investigate and fix
        ↓
   Framework re-runs validators
   ```

This is the correct architecture that matches your original bash implementation! 🎯
