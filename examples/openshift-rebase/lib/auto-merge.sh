#!/bin/bash

# Automated conflict resolution using Claude Code
# This function attempts to resolve merge conflicts automatically using Claude Code CLI
# with intelligent retry logic and comprehensive validation.

# Get library directory for sourcing test utilities
# Note: Don't override SCRIPT_DIR as it's set by the main script
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source test utilities for package extraction and guidance building
source "${LIB_DIR}/test-utils.sh"

# Initialize colors if terminal supports them
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  COLOR_RESET='\033[0m'
  COLOR_CYAN='\033[0;36m'
  COLOR_MAGENTA='\033[0;35m'
else
  COLOR_RESET=''
  COLOR_CYAN=''
  COLOR_MAGENTA=''
fi

auto_merge_conflicts() {
  local openshift_release="$1"
  local k8s_tag="$2"

  echo "Conflicts detected. Attempting automated resolution with RebaseAgent..."

  local max_attempts=100
  local attempt=1
  local resolved=false
  local previous_failure=""
  local failing_packages=""
  local start_time=$(date +%s)

  # Calculate optimal test parallelism based on available CPUs
  # Use environment variable if set, otherwise auto-calculate
  if [ -z "${KUBE_TEST_PARALLEL:-}" ]; then
    local available_cpus=$(nproc 2>/dev/null || echo "4")
    # Use half of available CPUs for conservative approach
    # This balances speed with memory usage (race detector overhead)
    KUBE_TEST_PARALLEL=$((available_cpus / 2))
    # Minimum of 1, maximum of 12 to avoid excessive memory usage
    KUBE_TEST_PARALLEL=$((KUBE_TEST_PARALLEL < 1 ? 1 : KUBE_TEST_PARALLEL))
    KUBE_TEST_PARALLEL=$((KUBE_TEST_PARALLEL > 12 ? 12 : KUBE_TEST_PARALLEL))
    echo "Auto-detected test parallelism: -parallel=$KUBE_TEST_PARALLEL (based on $available_cpus CPUs)"
  else
    echo "Using configured test parallelism: -parallel=$KUBE_TEST_PARALLEL"
  fi

  # Export as GOFLAGS so it's picked up by go test
  export GOFLAGS="${GOFLAGS:-} -parallel=$KUBE_TEST_PARALLEL"

  # Helper function to prefix output lines with attempt number and elapsed time
  prefix_lines() {
    local prefix="$1"
    local start_time="$2"
    while IFS= read -r line; do
      local elapsed=$(($(date +%s) - start_time))
      local elapsed_formatted
      if [ $elapsed -ge 60 ]; then
        elapsed_formatted=$(printf "%dm %ds" $((elapsed / 60)) $((elapsed % 60)))
      else
        elapsed_formatted="${elapsed}s"
      fi
      echo "[$prefix +${elapsed_formatted}] $line"
    done
  }

  while [ $attempt -le $max_attempts ] && [ "$resolved" = false ]; do
    echo ""
    echo "=== Attempt $attempt of $max_attempts ==="

    # Build the prompt for Claude based on attempt number
    local prompt
    if [ $attempt -eq 1 ]; then
      prompt="You are helping resolve merge conflicts during a Kubernetes rebase from OpenShift release branch '$openshift_release' to upstream Kubernetes tag '$k8s_tag'.

CONTEXT:
- 2/3 of conflicts typically stem from go.mod/go.sum files (resolve deterministically by accepting upstream changes)
- Most remaining conflicts are vendor/generation conflicts
- Few cases require manual intervention for conflicting business logic

# OPENSHIFT COMMIT CONVENTIONS:
# - UPSTREAM: <carry>: Changes we maintain in OpenShift that aren't yet upstream (preserve these)
# - UPSTREAM: <drop>: Changes being removed/discarded (no longer needed or integrated upstream)
# When resolving conflicts, preserve <carry> changes and understand that <drop> commits indicate intentional removal.

# CONFLICT VISUALIZATION SETUP:
# Ensure git is configured with: git config merge.conflictstyle diff3
# This shows three sections: HEAD (ours), base (original), MERGE_HEAD (theirs)
# Seeing the base helps understand what BOTH sides changed, not just the difference.

INVESTIGATIVE TOOLS - Use git and gh commands to understand changes:

AVAILABLE TOOLS:
- git: Use for examining commits, blame, history, diffs
  Run 'git --help' or 'git <command> --help' to learn usage
- gh: GitHub CLI for finding and viewing PRs
  Run 'gh --help', 'gh pr --help', 'gh pr list --help', etc. to learn usage

INVESTIGATION WORKFLOW (Commit -> PR -> Context):
When you encounter a complex code conflict:
1. Use 'git blame <file>' to find which commit introduced the conflicting lines
2. # Check commit messages (git log) for <carry> and <drop> tags to understand OpenShift's intent
3. # Use 'git log --oneline HEAD..MERGE_HEAD' to see upstream commits being merged in
4. # Use 'git log --oneline MERGE_HEAD..HEAD' to see OpenShift commits that might conflict
5. Use 'gh pr list' to search for PRs containing that commit hash
   - Search in both repos: kubernetes/kubernetes and openshift/kubernetes
   - Use --help to learn search options if needed
6. Use 'gh pr view' to read the PR description and understand the motivation
7. Use 'git show' or 'git log' to view commit details if needed
8. Make informed merge decisions based on understanding WHY both changes were made

KEY PRINCIPLES:
- If unsure about command syntax, use --help to check available options
- Investigate complex code conflicts (not go.mod/vendor/generated files)
- Determine if OpenShift changes are workarounds, features, or fixes
- Preserve important OpenShift customizations while accepting upstream improvements

# CONFLICT RESOLUTION ORDER (resolve in this sequence for best results):
# 1. FIRST: Dependency files (go.mod, go.sum) - Accept upstream, deterministic
# 2. SECOND: Generated files (zz_generated.*, *.pb.go, api/openapi-spec/) - Will be regenerated
# 3. THIRD: Vendored dependencies (vendor/) - Will be regenerated by hack/update-vendor.sh
# 4. FOURTH: Build/tooling files (Makefile, hack/, scripts/) - Check if OpenShift customizations still needed
# 5. FIFTH: OpenShift-specific files (openshift-hack/, OWNERS) - Always preserve OpenShift changes
# 6. LAST: Core business logic (pkg/, cmd/, staging/) - Requires careful investigation
# RATIONALE: Resolving easy→hard minimizes cascading conflicts and provides clean foundation.

# SEMANTIC CONFLICT DETECTION (check after resolving textual conflicts):
# 1. API Changes: Do both sides modify same API differently? (signatures, types, compatibility)
# 2. Behavior Changes: Do both sides change same behavior? (features, bug fixes, expectations)
# 3. Dependency Conflicts: Do both sides require different versions? (go.mod, transitive deps)
# 4. Build Conflicts: Do both sides modify build differently? (Makefile, flags, tool versions)
# VALIDATION: Run tests to catch semantic conflicts that passed textual merge but break functionality.

YOUR TASK:
0. Assess conflict complexity:
   - Count conflicted files and categorize (go.mod/vendor/generated/code)
   - Simple (<10 files, mostly deps): Quick resolution, accept upstream
   - Moderate (10-30 files, mixed): Categorize first, investigate code conflicts
   - Complex (30-50 files, many code): Careful investigation, consider manual help
   - Critical (50+ files): STOP and consult team
1. Identify all conflicted files using 'git status'
2. Resolve conflicts following these guidelines:
   - go.mod/go.sum: Accept upstream changes (<<<<<<< HEAD sections), then run 'go mod tidy'
   - vendor/: Usually generated, will be regenerated later - prefer upstream version
   - Generated files: Prefer upstream version
   - OpenShift-specific files (openshift-hack/, OWNERS, etc.): Preserve OpenShift changes
   - Code conflicts:
     * First, investigate using git and gh commands (use --help if unsure of syntax)
     * Understand the intent behind both changes by finding related commits and PRs
     * Merge carefully, preserving OpenShift customizations while accepting upstream improvements
     * Document your reasoning if you make a non-obvious choice
3. Stage all resolved files with 'git add <file>'

# IMPORTANT: Do NOT run 'go mod tidy', 'hack/install-etcd.sh', 'hack/update-vendor.sh', 'make update', 'make', or 'make test' manually.
# These will be run automatically in a container with the correct Go version and tools after you finish (etcd will be installed automatically).
#
# Do NOT edit files in the vendor/ directory manually. These are generated files that will be regenerated by hack/update-vendor.sh.
#
# VENDOR FILE CONFLICTS - Special handling required:
# When vendor/ code is incompatible or causing build/test failures:
# 1. DO NOT edit vendor/ files directly (they will be regenerated)
# 2. Check if go.mod needs updating to newer version of the dependency
# 3. Or add 'replace' directive in go.mod to use patched fork
# 4. Or modify the calling code (non-vendor files) to use different/compatible API
# 5. If truly stuck, document the issue and continue with other conflicts - mark for manual review
#
# Do NOT commit anything. Just resolve conflicts and stage the resolved files."
    else
      prompt="Retry attempt $attempt of $max_attempts for Kubernetes rebase conflict resolution from '$openshift_release' to '$k8s_tag'.

PREVIOUS ATTEMPT FAILED WITH:
$previous_failure

COMMON BUILD ERROR PATTERNS:
- \"undefined: SomeType\" → Type moved/renamed (search: git grep \"type SomeType\" MERGE_HEAD)
- \"cannot use X as Y\" → Function signature changed (compare signatures)
- \"package X not in GOROOT\" → Vendor mismatch (re-run: go mod tidy)
- \"missing go.sum entry\" → go.mod/go.sum out of sync (always run: go mod tidy)

Check if current failure matches a pattern above, then apply fix strategy.

INVESTIGATIVE TOOLS available:
- git (git blame, git log, git show) - Examine commits and history
- gh (gh pr list, gh pr view) - Find and read PRs in kubernetes/kubernetes and openshift/kubernetes
- Use --help on any command to learn options if unsure

Follow: git blame -> gh pr list (search commit) -> gh pr view (understand context) -> informed decision

Please analyze the failure above and try a different approach to resolve the conflicts.
Remember to:
1. Check 'git status' for remaining conflicts
2. For complex code conflicts, use git blame/log and gh commands to understand context
3. Resolve all conflicts carefully
4. Stage resolved files with 'git add <file>'

# Do NOT run 'go mod tidy', 'make update', 'make', or 'make test' manually. These will be run automatically in a container after you finish.
# Do NOT edit files in the vendor/ directory manually. These are generated files that will be regenerated by hack/update-vendor.sh.
#
# VENDOR FILE CONFLICTS - Special handling required:
# When vendor/ code is incompatible or causing build/test failures:
# 1. DO NOT edit vendor/ files directly (they will be regenerated)
# 2. Check if go.mod needs updating to newer version of the dependency
# 3. Or add 'replace' directive in go.mod to use patched fork
# 4. Or modify the calling code (non-vendor files) to use different/compatible API
# 5. If truly stuck, document the issue and continue with other conflicts - mark for manual review
#
# Do NOT commit anything. Focus on fixing the specific code errors shown above."
    fi

    # Show retry context to user if this is a retry attempt
    if [ $attempt -gt 1 ]; then
      echo ""
      echo "========================================================================"
      echo "RETRY CONTEXT - Showing RebaseAgent the previous failure:"
      echo "========================================================================"
      echo "$previous_failure"
      echo "========================================================================"
      echo ""
    fi

    # Invoke Claude Code with the prompt (non-interactive mode with permissions bypass)
    echo "Invoking RebaseAgent to resolve conflicts..."
    echo "========================================================================"
    local claude_output=$(mktemp)
    local claude_raw_output=$(mktemp)

    # Use streaming JSON with verbose to see all details, parse and display in real-time
    # No timeout - allow Claude to run as long as needed for complex conflict resolution
    local text_block_started=false
    claude --print --dangerously-skip-permissions --verbose --output-format=stream-json --include-partial-messages "$prompt" 2>&1 | tee "$claude_raw_output" | while IFS= read -r line; do
      # Parse JSON and display human-readable output
      local event_type=$(echo "$line" | jq -r '.type' 2>/dev/null)

      if [ "$event_type" = "stream_event" ]; then
        local stream_type=$(echo "$line" | jq -r '.event.type // empty' 2>/dev/null)

        # Detect start of new text block
        if [ "$stream_type" = "content_block_start" ]; then
          local block_type=$(echo "$line" | jq -r '.event.content_block.type // empty' 2>/dev/null)
          if [ "$block_type" = "text" ]; then
            local elapsed=$(($(date +%s) - start_time))
            local elapsed_formatted
            if [ $elapsed -ge 60 ]; then
              elapsed_formatted=$(printf "%dm %ds" $((elapsed / 60)) $((elapsed % 60)))
            else
              elapsed_formatted="${elapsed}s"
            fi
            printf "\n[Attempt $attempt +${elapsed_formatted}] ${COLOR_MAGENTA}RebaseAgent:${COLOR_RESET} "
            text_block_started=true
          fi
        # Handle streaming text deltas - print without newline
        elif [ "$stream_type" = "content_block_delta" ]; then
          local delta_type=$(echo "$line" | jq -r '.event.delta.type // empty' 2>/dev/null)
          if [ "$delta_type" = "text_delta" ]; then
            echo "$line" | jq -r '.event.delta.text' 2>/dev/null | tr -d '\n'
          fi
        fi
      elif [ "$event_type" = "assistant" ]; then
        # Complete message - print with newline
        local elapsed=$(($(date +%s) - start_time))
        local elapsed_formatted
        if [ $elapsed -ge 60 ]; then
          elapsed_formatted=$(printf "%dm %ds" $((elapsed / 60)) $((elapsed % 60)))
        else
          elapsed_formatted="${elapsed}s"
        fi
        echo "$line" | jq -r '.message.content[] |
          if .type == "text" then
            "\n"
          elif .type == "tool_use" then
            "\n[Attempt '"$attempt"' +'"$elapsed_formatted"'] ▶ Executing: " + .name + " {" + (.input.command // (.input.description // (.input.file_path // ""))) + "}"
          else
            empty
          end
        ' 2>/dev/null | while IFS= read -r output_line; do
          if [[ "$output_line" == *"▶ Executing:"* ]]; then
            echo -e "${output_line//▶ Executing:/${COLOR_CYAN}▶ Executing:${COLOR_RESET}}"
          else
            echo "$output_line"
          fi
        done
      elif [ "$event_type" = "user" ]; then
        # Tool results - show actual output
        local elapsed=$(($(date +%s) - start_time))
        local elapsed_formatted
        if [ $elapsed -ge 60 ]; then
          elapsed_formatted=$(printf "%dm %ds" $((elapsed / 60)) $((elapsed % 60)))
        else
          elapsed_formatted="${elapsed}s"
        fi
        echo "$line" | jq -r '.message.content[] |
          if .type == "tool_result" and .is_error == false then
            "\n[Attempt '"$attempt"' +'"$elapsed_formatted"'] ✓ Completed:\n" + .content
          elif .type == "tool_result" and .is_error == true then
            "\n[Attempt '"$attempt"' +'"$elapsed_formatted"'] ✗ Error: " + .content
          else
            empty
          end
        ' 2>/dev/null
      elif [ "$event_type" = "result" ]; then
        echo "$line" | jq -r '
          if .subtype == "success" then
            "\n\n========================================================================\n✓ Claude completed in " + (.duration_ms | tostring) + "ms (" + (.num_turns | tostring) + " turns)"
          else
            empty
          end
        ' 2>/dev/null
      fi
    done | tee "$claude_output"
    local claude_exit_code=$?

    if [ $claude_exit_code -eq 0 ]; then
      echo "========================================================================"
      echo "RebaseAgent execution completed. Verifying resolution..."
      rm -f "$claude_output" "$claude_raw_output"

      # Check if conflicts are resolved
      if git diff --check &>/dev/null && ! git status | grep -q "Unmerged paths"; then
        echo "✓ Conflicts appear to be resolved."

        # Run container operations to update vendor and generate code
        # Skip if in test mode (REBASER_SKIP_CONTAINER_OPS is set)
        if [ -z "${REBASER_SKIP_CONTAINER_OPS:-}" ] && [ -n "${REBASER_CONTAINER_IMAGE:-}" ]; then
          echo "Running container operations (go mod tidy, install etcd, hack/update-vendor.sh, make update)..."

          # Determine setup commands based on container image
          local setup_cmd=""
          if [[ "${REBASER_CONTAINER_IMAGE}" == "golang:"* ]]; then
            # golang image needs jq, protoc 23.4, iproute2 (for ss), and rsync installed
            setup_cmd="apt-get update -qq && apt-get install -y -qq jq unzip wget iproute2 rsync && \
wget -q https://github.com/protocolbuffers/protobuf/releases/download/v23.4/protoc-23.4-linux-x86_64.zip && \
unzip -q protoc-23.4-linux-x86_64.zip -d /usr/local && \
rm protoc-23.4-linux-x86_64.zip && "
          fi

          if ${REBASER_CONTAINER_RUNTIME:-podman} run -it --rm -v "$(pwd):/go/k8s.io/kubernetes${REBASER_SELINUX_FLAG}" \
            --workdir=/go/k8s.io/kubernetes \
            "${REBASER_CONTAINER_IMAGE}" \
            bash -c "${setup_cmd}go mod tidy && source hack/install-etcd.sh && hack/update-vendor.sh && make update" 2>&1 | prefix_lines "Attempt $attempt" "$start_time" | tee container_output.log; then
            echo "✓ Container operations completed successfully."
          else
            echo "✗ Container operations failed."
            previous_failure="Container operations (go mod tidy, install etcd, hack/update-vendor.sh, make update) failed:

$(tail -100 container_output.log)

Please fix the code issues that are causing the build to fail."
            attempt=$((attempt + 1))
            continue
          fi
        fi

        # Check if build succeeds
        echo "Running 'make' to verify build..."
        if make 2>&1 | prefix_lines "Attempt $attempt" "$start_time" | tee make_output.log; then
          echo "✓ Build successful."

          # Hybrid test verification strategy
          local test_passed=false

          if [ -n "$failing_packages" ] && [ $attempt -gt 1 ]; then
            # Retry attempt with known failing packages - run targeted tests first
            echo "Running targeted tests for previously failing packages..."
            echo "Packages: $failing_packages"

            if make test WHAT="$failing_packages" 2>&1 | prefix_lines "Attempt $attempt" "$start_time" | tee test_output.log; then
              echo "✓ Targeted tests passed!"
              echo "Running full test suite for comprehensive verification..."

              # Targeted tests passed, now run full suite to catch regressions
              if make test 2>&1 | prefix_lines "Attempt $attempt" "$start_time" | tee test_output.log; then
                echo "✓ Full test suite passed!"
                test_passed=true
              else
                echo "✗ Full test suite found new failures."
                # Extract new failing packages from full test
                failing_packages=$(test_extract_failing_packages test_output.log)
              fi
            else
              echo "✗ Targeted tests still failing."
              # Update failing packages from targeted test output
              failing_packages=$(test_extract_failing_packages test_output.log)
            fi
          else
            # First attempt or no known failures - run full test suite
            echo "Running full test suite..."
            echo "(Test output will be shown below)"

            if make test 2>&1 | prefix_lines "Attempt $attempt" "$start_time" | tee test_output.log; then
              echo "✓ Tests passed!"
              test_passed=true
            else
              echo "✗ Tests failed."
              # Extract failing packages for next retry
              failing_packages=$(test_extract_failing_packages test_output.log)
            fi
          fi

          # Check if tests passed
          if [ "$test_passed" = true ]; then
            echo ""
            echo "SUCCESS: Automated resolution completed after $attempt attempt(s)."
            resolved=true
            rm -f make_output.log test_output.log "$claude_output" "$claude_raw_output"
          else
            # Build test guidance for retry
            local test_guidance=$(test_build_guidance "$failing_packages")

            previous_failure="TESTS FAILED (exit code: $?):${test_guidance}\n\nLast 100 lines of output:\n$(tail -100 test_output.log)"
            attempt=$((attempt + 1))
          fi
        else
          echo "✗ Build failed."
          previous_failure="BUILD FAILED (exit code: $?):\n\nLast 100 lines of output:\n$(tail -100 make_output.log)"
          attempt=$((attempt + 1))
        fi
      else
        echo "✗ Conflicts still remain."
        local conflicted_files=$(git status --porcelain | grep '^UU\|^AA\|^DD' || git diff --name-only --diff-filter=U)
        previous_failure="CONFLICTS STILL REMAIN:\n\nConflicted files:\n$conflicted_files\n\nGit status:\n$(git status)"
        attempt=$((attempt + 1))
      fi
    else
      echo "========================================================================"
      echo "✗ RebaseAgent invocation failed with exit code: $claude_exit_code"
      previous_failure="CLAUDE CODE EXECUTION FAILED:\n\nExit code: $claude_exit_code\n\nLast 50 lines of output:\n$(tail -50 "$claude_output")"
      rm -f "$claude_output" "$claude_raw_output"
      attempt=$((attempt + 1))
    fi

    # Small delay between attempts
    if [ "$resolved" = false ] && [ $attempt -le $max_attempts ]; then
      echo ""
      echo "Preparing for next attempt..."
      sleep 2
    fi
  done

  # Commit based on resolution outcome
  if [ "$resolved" = true ]; then
    echo ""
    echo "Committing automated conflict resolution..."
    git commit -am "UPSTREAM: <drop>: automated conflict resolution via Claude Code ($attempt attempts)"
    echo "✓ Conflicts resolved and committed successfully!"
    return 0
  else
    echo ""
    echo "======================================================================"
    echo "AUTOMATED RESOLUTION FAILED after $max_attempts attempts."
    echo "======================================================================"
    echo "Falling back to manual resolution..."
    echo ""
    git status
    echo ""
    echo "Please resolve conflicts manually in another terminal."
    echo "After resolving, stage files with 'git add' and then continue."
    echo ""
    read -n 1 -s -r -p "PRESS ANY KEY TO CONTINUE"
    echo ""
    git commit -am "UPSTREAM: <drop>: manually resolve conflicts"
    return 1
  fi
}
