# Hello World Conflict Resolution Example

This example demonstrates how Alphanso uses Claude Code Agent SDK to automatically resolve git merge conflicts.

## What This Example Does

1. **Setup Phase**: Creates two git repositories (upstream and fork) with conflicting changes
2. **Pre-Actions**: Fetches upstream and attempts to merge (creates conflict)
3. **Validation**: Detects merge conflict using GitConflictValidator
4. **AI Fix**: Claude investigates the conflict and resolves it using SDK tools
5. **Re-Validation**: Confirms the conflict is resolved

## Directory Structure

```
hello-world-conflict/
├── config.yaml              # Convergence configuration
├── prompts/
│   └── conflict-resolver.txt  # Custom system prompt
├── setup.sh                 # Creates git conflict scenario
├── run.sh                   # Runs the example
├── README.md                # This file
└── .gitignore               # Ignore git-repos/
```

## How to Run

```bash
# From this directory
./run.sh
```

Or step-by-step:

```bash
# 1. Create git repositories with conflict
./setup.sh

# 2. Run convergence loop from fork directory
cd git-repos/fork
alphanso run --config ../../config.yaml --verbose
```

## Logging Options

Control output verbosity with logging flags:

```bash
# Default (WARNING): Only errors and warnings
alphanso run --config config.yaml

# INFO level (-v): Show progress and key events
alphanso run --config config.yaml -v

# DEBUG level (-vv): Show detailed diagnostics including AI context
alphanso run --config config.yaml -vv

# Save logs to file (text format)
alphanso run --config config.yaml -vv --log-file debug.log

# Save logs to file (JSON format for parsing)
alphanso run --config config.yaml -v --log-file logs.json --log-format json

# Quiet mode: Only errors
alphanso run --config config.yaml -q
```

**Recommended for debugging**:
```bash
# See exactly what context is sent to Claude
alphanso run --config config.yaml -vv --log-file debug.log
grep "CONTEXT SENT TO AI" debug.log -A 50
```

## Expected Behavior

### Attempt 1: Detect Conflict

```
NODE: pre_actions
[1/2] Fetch upstream changes → ✅ Success
[2/2] Attempt merge (will conflict) → ✅ Success

NODE: validate
[1/1] Git Conflict Check → ❌ Failed

NODE: decide
❌ Validation failed (attempt 1/5)
Decision: RETRY (increment attempt and re-validate)
```

### Attempt 2: AI Resolves Conflict

```
NODE: ai_fix
Invoking Claude Agent SDK to investigate and fix failures...

Claude investigates:
- Uses Bash tool: git status
- Uses Read tool: README.md (sees conflict markers)
- Uses Bash tool: git diff

Claude resolves:
- Uses Edit tool: removes conflict markers, merges changes
- Uses Bash tool: git add README.md
- Uses Bash tool: git commit -m "Merge v2.0.0: integrate upstream changes"

✅ Claude used 7 SDK tools

NODE: validate
[1/1] Git Conflict Check → ✅ Success

NODE: decide
✅ All validators passed
Decision: END with success
```

### Final Result

```
✅ All validators PASSED
Completed in 2 attempts
Total duration: ~30 seconds
```

## The Conflict Scenario

**Upstream (v2.0.0)**:
```markdown
# Hello World Project

Version: 2.0.0

## Features
- Feature A (enhanced)
- Feature B (enhanced)
- Feature C (new)
```

**Fork (modified)**:
```markdown
# Hello World Project - Forked Edition

Version: 1.0.0-fork

## Features
- Feature A (fork-specific)
- Feature B (fork-specific)
- Feature D (fork-only)
```

**Claude's Resolution** (example):
```markdown
# Hello World Project - Forked Edition

Version: 2.0.0-fork

## Features
- Feature A (enhanced, fork-specific)
- Feature B (enhanced, fork-specific)
- Feature C (new)
- Feature D (fork-only)
```

## Custom System Prompt

This example uses a custom system prompt (`prompts/conflict-resolver.txt`) that defines Claude's role as a "git merge conflict resolution assistant". This prompt is loaded automatically by the configuration system.

## Key Features Demonstrated

- ✅ Custom system prompts via `system_prompt_file`
- ✅ Claude SDK's built-in tools (Bash, Read, Edit)
- ✅ GitConflictValidator integration
- ✅ Pre-actions for setup
- ✅ Convergence loop with retry
- ✅ Local git repository management

## Requirements

- Python 3.11+
- Alphanso installed (`pip install -e .` from project root)
- `ANTHROPIC_API_KEY` environment variable set
- Git installed

## Notes

- The `git-repos/` directory is created by `setup.sh` and gitignored
- The example is self-contained - no external dependencies needed
- You can inspect the git history after running: `cd git-repos/fork && git log --oneline`
