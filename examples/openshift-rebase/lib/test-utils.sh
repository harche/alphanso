#!/usr/bin/env bash
# Test utility functions for running and analyzing Kubernetes tests

# Extract failing package paths from test output
# Args:
#   $1: Path to test output log file
# Returns:
#   Space-separated list of failing package paths (e.g., "./pkg/controller/job ./pkg/scheduler ")
test_extract_failing_packages() {
  local test_output_file="$1"

  if [ ! -f "$test_output_file" ]; then
    echo ""
    return 1
  fi

  # Match the exact logic used in auto-merge.sh
  grep -E "^(FAIL|---\s+FAIL:)" "$test_output_file" 2>/dev/null | \
    grep -oE "k8s\.io/kubernetes/[^[:space:]]+" | \
    sort -u | \
    sed 's|k8s.io/kubernetes/|./|' | \
    head -10 | \
    tr '\n' ' ' || true
}

# Run targeted tests for specific packages
# Args:
#   $1: Space-separated list of packages (e.g., "./pkg/controller/job ./pkg/scheduler")
#   $2: Output file path
# Returns:
#   0 if tests pass, non-zero otherwise
test_run_targeted() {
  local packages="$1"
  local output_file="$2"

  if [ -z "$packages" ]; then
    echo "Error: No packages specified for targeted testing"
    return 1
  fi

  make test WHAT="$packages" &>"$output_file"
}

# Run full test suite
# Args:
#   $1: Output file path
# Returns:
#   0 if tests pass, non-zero otherwise
test_run_full() {
  local output_file="$1"
  make test &>"$output_file"
}

# Build test guidance message for retry
# Args:
#   $1: Space-separated list of failing packages
# Returns:
#   Formatted guidance string for Claude's retry prompt
test_build_guidance() {
  local failing_packages="$1"
  local test_guidance=""

  if [ -n "$failing_packages" ]; then
    # Count packages
    local pkg_count=$(echo "$failing_packages" | wc -w)

    test_guidance="\n\nFailing packages detected ($pkg_count packages):\n$failing_packages\n\nAfter fixing, verify with targeted tests first:\n"
    for pkg in $failing_packages; do
      test_guidance="${test_guidance}  make test WHAT=$pkg\n"
    done
    test_guidance="${test_guidance}\nOnce targeted tests pass, run full 'make test' to ensure no regressions."
  else
    test_guidance="\n\nAfter fixing, run 'make test' to verify."
  fi

  echo -e "$test_guidance"
}
