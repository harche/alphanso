# OpenShift Kubernetes Rebase Example

This example demonstrates how Alphanso automates the complex process of rebasing OpenShift's Kubernetes fork against upstream Kubernetes releases.

## The Problem

Rebasing a large fork like OpenShift's Kubernetes against upstream involves:

- Fetching and merging upstream tags
- Resolving merge conflicts across hundreds of files
- Updating generated code and dependencies
- Running build processes and fixing compilation errors
- Ensuring all unit tests pass

**Manual Process** (error-prone and time-consuming):
1. Fetch upstream tag
2. Merge into OpenShift release branch → conflicts
3. Manually resolve conflicts
4. Run `make update` → fails with outdated generated code
5. Fix code generation issues
6. Run `make` → build failures
7. Fix compilation errors
8. Run `make test` → test failures
9. Fix test issues
10. Repeat steps 4-9 until everything passes

This process can take hours or even days and requires deep knowledge of both codebases.

## The Solution

Alphanso automates this with AI:

1. **Pre-action**: Sets up the Kubernetes fork repository
2. **Main Script**: Performs the rebase operation (retries until success)
3. **Validators**: Detect failures (make update, build, tests)
4. **AI Fix**: Claude investigates errors and fixes code
5. **Re-run**: Framework re-runs main script and validators
6. **Iterate**: Continues until all validators pass

**Result**: Automated rebase with minimal human intervention.

## What This Example Does

### The Scenario

Rebasing OpenShift's Kubernetes fork from one upstream version to another:

**Before**: OpenShift release-4.22 based on Kubernetes v1.34.x
**After**: OpenShift release-4.22 rebased to Kubernetes v1.35.0-alpha.2

### Typical Issues During Rebase

1. **Merge conflicts**: Code changes in both upstream and OpenShift
2. **Generated code outdated**: Proto files, API definitions need regeneration
3. **API changes**: Upstream changed function signatures
4. **Import path changes**: Packages moved or renamed
5. **Test failures**: Tests need updates for new behavior
6. **Build failures**: Compilation errors from breaking changes

### AI Convergence Flow

**Attempt 1: Initial Rebase**
```
NODE: pre_actions
[1/1] Setup kubernetes fork repository → ✅ Success

NODE: main_script
Rebase OpenShift kubernetes fork to upstream tag → ❌ Failed
  Merge conflicts detected

NODE: validate (skipped - main script failed)

NODE: decide
❌ Main script failed (attempt 1/100)
Decision: RETRY
```

**Attempt 2: AI Resolves Conflicts**
```
NODE: ai_fix
Invoking Claude Agent SDK to investigate and fix failures...

💭 Claude investigates:
   🔧 Bash: git status
   🔧 Bash: git diff
   📖 Read: pkg/controller/replication/replication_controller.go
   💭 Thinking: Analyzing merge conflict patterns...

💭 Claude resolves:
   ✏️ Edit: pkg/controller/replication/replication_controller.go
   ✏️ Edit: pkg/kubelet/kubelet.go
   🔧 Bash: git add .
   🔧 Bash: git commit -m "Merge v1.35.0-alpha.2: resolve conflicts"

✅ Claude used 8 SDK tools

NODE: main_script
Rebase OpenShift kubernetes fork to upstream tag → ✅ Success

NODE: validate
[1/3] Make update → ❌ Failed
  Generated files out of sync
[2/3] Build → ⏭️ Skipped
[3/3] Unit Tests → ⏭️ Skipped

NODE: decide
❌ Validation failed (attempt 2/100)
Decision: RETRY
```

**Attempt 3-8: AI Iteratively Fixes Issues**
```
NODE: ai_fix
Invoking Claude Agent SDK to investigate and fix failures...

💭 Claude investigates:
   🔧 Bash: source hack/install-etcd.sh && make update
   📖 Read: error output
   💭 Thinking: Proto files need regeneration...

💭 Claude fixes:
   🔧 Bash: make update
   🔧 Bash: git add .
   🔧 Bash: git commit -m "Regenerate code"

✅ Claude used 5 SDK tools

... (iterations continue, fixing build errors, test failures, etc.) ...

NODE: main_script
Rebase OpenShift kubernetes fork to upstream tag → ✅ Success

NODE: validate
[1/3] Make update → ✅ Success
[2/3] Build → ✅ Success
[3/3] Unit Tests → ✅ Success

NODE: decide
✅ All validators PASSED
Decision: END with success
```

**Typical Result**: ✅ Completed in 7-8 attempts (~1 hour)

The exact number of attempts varies depending on the complexity of merge conflicts and the extent of API changes between versions. Each iteration allows Claude to investigate errors, fix code, and re-run validators until all checks pass.

## How to Run

### Quick Start
```bash
./run.sh
```

### Step-by-Step
```bash
# 1. Set up environment (requires your fork repository)
./setup.sh --fork-repo=git@github.com:YOUR-USERNAME/kubernetes.git

# 2. Run convergence
cd kubernetes
uv run alphanso run --config ../config.yaml

# Alternatively, run from example directory
cd ..
uv run alphanso run --config config.yaml
```

### Logging Options

Control output verbosity with logging flags:

```bash
# Default (INFO): Show validator results, AI actions, context
uv run alphanso run --config config.yaml

# DEBUG level (-v): Add workflow tracking and detailed tool I/O
uv run alphanso run --config config.yaml -v

# TRACE level (-vv): Add state dumps and development diagnostics
uv run alphanso run --config config.yaml -vv

# Quiet mode: Only errors
uv run alphanso run --config config.yaml -q

# Save logs to file for later analysis
uv run alphanso run --config config.yaml --log-file rebase.log

# Save logs in JSON format for parsing
uv run alphanso run --config config.yaml --log-file rebase.json --log-format json
```

**Debugging tips**:
```bash
# Default output shows context sent to Claude and tool usage
uv run alphanso run --config config.yaml

# Add workflow tracking to see state transitions
uv run alphanso run --config config.yaml -v --log-file debug.log
grep "Entering\|Routing" debug.log

# Full diagnostics with state dumps
uv run alphanso run --config config.yaml -vv --log-file trace.log
```

## Directory Structure

```
openshift-rebase/
├── config.yaml              # Convergence configuration
├── setup.sh                 # Clones fork and configures remotes
├── ocp-rebase.sh            # Main rebase script
├── run.sh                   # Convenience script to run the example
├── prompts/
│   └── rebase-assistant.txt # Custom system prompt for AI
├── lib/
│   ├── auto-merge.sh        # Auto-merge utilities
│   └── ci-image-setup.sh    # CI image helpers
├── .gitignore               # Ignore kubernetes/ directory
└── README.md                # This file
```

## Configuration Details

### Pre-action
- Clones your Kubernetes fork repository
- Sets up `upstream` (kubernetes/kubernetes) and `openshift` (openshift/kubernetes) remotes
- Validates repository configuration

### Main Script (Retries Until Success)
- Fetches upstream tag (e.g., v1.35.0-alpha.2)
- Fetches OpenShift release branch (e.g., release-4.22)
- Creates rebase branch
- Performs git merge
- Handles merge conflicts

### Validators (Only Run If Main Script Succeeds)
1. **Make update**: Regenerates code (proto, API definitions, docs)
2. **Build**: Compiles Kubernetes binaries
3. **Unit Tests**: Runs test suite

## Requirements

- Python 3.11+
- Alphanso installed (`pip install -e /path/to/alphanso`)
- `ANTHROPIC_API_KEY` environment variable set
- Git installed
- Go toolchain (for building Kubernetes)
- jq, podman (for Kubernetes build process)
- A fork of kubernetes/kubernetes on GitHub

## Custom System Prompt

This example uses a custom system prompt (`prompts/rebase-assistant.txt`) that defines Claude's role as a "Kubernetes rebase assistant" with knowledge of:

- Git merge conflict resolution
- Kubernetes codebase structure
- Go programming patterns
- Code generation workflows
- Build and test processes

## Key Features Demonstrated

- ✅ **Script-centric workflow**: Main script retries until success
- ✅ **Hybrid retry strategy**: Smart decision between re-running main script or going to AI
- ✅ **Custom system prompts**: Specialized knowledge for the task
- ✅ **Multiple validators**: Update, build, and test validation
- ✅ **Long-running operations**: Timeouts up to 30 minutes
- ✅ **Real-world complexity**: Actual OpenShift rebase automation

## Extending This Pattern

This example can be adapted for:

- **Other Kubernetes distributions**: Rancher, Amazon EKS, Azure AKS
- **Other large forks**: Chromium forks, Linux kernel forks
- **CI/CD integration**: Automate rebases in your pipeline
- **Automated PR creation**: Use `gh` CLI to create pull requests
- **Custom conflict strategies**: Add domain-specific merge rules

## Troubleshooting

**Setup fails**:
- Ensure you have a fork of kubernetes/kubernetes
- Check SSH keys are configured for GitHub
- Verify prerequisites: `git --version`, `jq --version`, `podman --version`

**Rebase fails repeatedly**:
- Check the conflicts are within scope (too many conflicts may need manual intervention)
- Increase `max_attempts` in config.yaml
- Review logs with `-v` flag to see AI's reasoning

**Build or test failures**:
- Ensure you have Go toolchain installed
- Check disk space (Kubernetes build requires several GB)
- Verify etcd is installed: `source hack/install-etcd.sh`

**Repository configuration errors**:
- Run `./setup.sh` again to reconfigure remotes
- Manually verify remotes: `cd kubernetes && git remote -v`

## Notes

- The `kubernetes/` directory is created by `setup.sh` and gitignored
- This is a real-world example - it actually performs OpenShift rebases
- First run may take longer as dependencies are downloaded
- The example uses a large codebase - be patient with build times
- You can inspect the git history after running: `cd kubernetes && git log --oneline`

## Safety

This example creates a new branch for rebasing and does not modify your main branches. All changes are local until you explicitly push them.
