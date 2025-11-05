#!/bin/bash

# OpenShift Kubernetes Repository Setup
#
# This script performs one-time setup of the Kubernetes repository for rebasing.
# It clones your fork and configures the required remotes.
#
# Requirements: git, jq, podman

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Allow override for testing
KUBE_DIR="${REBASER_KUBE_DIR:-${SCRIPT_DIR}/kubernetes}"

# Arguments
fork_repo=""

usage() {
  echo "OpenShift Kubernetes Repository Setup"
  echo ""
  echo "Usage: $0 --fork-repo=<repo>"
  echo ""
  echo "Required arguments:"
  echo "  --fork-repo=<repo>           Your fork repository (URL or local path)"
  echo ""
  echo "Examples:"
  echo "  # With remote GitHub repository:"
  echo "  $0 --fork-repo=git@github.com:harche/kubernetes.git"
  echo ""
  echo "  # With HTTPS URL:"
  echo "  $0 --fork-repo=https://github.com/harche/kubernetes.git"
  echo ""
  echo "  # With local repository (for testing):"
  echo "  $0 --fork-repo=/path/to/local/fork"
}

# Parse arguments
for i in "$@"; do
  case $i in
    --fork-repo=*)
      fork_repo="${i#*=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $i"
      echo ""
      usage
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$fork_repo" ]; then
  echo "Error: Required argument missing: --fork-repo"
  echo ""
  usage
  exit 1
fi

echo "======================================================================"
echo "OpenShift Kubernetes Repository Setup"
echo "======================================================================"
echo "Fork repository: $fork_repo"
echo "Target directory: $KUBE_DIR"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
for cmd in git jq podman; do
  if ! command -v $cmd &>/dev/null; then
    echo "Error: $cmd not installed"
    exit 1
  fi
done
echo "✓ All prerequisites installed (git, jq, podman)"
echo ""

# Clone kubernetes directory if it doesn't exist
if [ -d "$KUBE_DIR" ]; then
  echo "Repository directory already exists: $KUBE_DIR"
  echo "Skipping clone. Using existing repository."
  echo ""
else
  echo "Cloning your Kubernetes fork..."
  git clone "$fork_repo" "$KUBE_DIR"

  if [ ! -d "$KUBE_DIR" ]; then
    echo "Error: Failed to clone repository"
    exit 1
  fi

  echo "✓ Repository cloned successfully"
  echo ""
fi

# Change to kubernetes directory
cd "$KUBE_DIR"

# Verify we're not using upstream or openshift as origin
echo "Verifying repository configuration..."
origin=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$origin" =~ .*kubernetes/kubernetes.* ]] || [[ "$origin" =~ .*openshift/kubernetes.* ]]; then
  echo "Error: origin points to kubernetes/kubernetes or openshift/kubernetes"
  echo "Origin must be your personal fork. Found: $origin"
  exit 1
fi
echo "✓ Origin is correctly set to personal fork: $origin"
echo ""

# Add upstream and openshift remotes if they don't exist
# Support environment variables for testing with local repositories
UPSTREAM_REPO="${REBASER_UPSTREAM_REPO:-git@github.com:kubernetes/kubernetes.git}"
OPENSHIFT_REPO="${REBASER_OPENSHIFT_REPO:-git@github.com:openshift/kubernetes.git}"

echo "Setting up git remotes..."
git remote add upstream "$UPSTREAM_REPO" 2>/dev/null || echo "  upstream remote already exists"
git remote add openshift "$OPENSHIFT_REPO" 2>/dev/null || echo "  openshift remote already exists"
echo "✓ Remotes configured:"
echo "  - upstream: $UPSTREAM_REPO"
echo "  - openshift: $OPENSHIFT_REPO"
echo ""

echo "======================================================================"
echo "✓ Setup complete!"
echo "======================================================================"
echo "Repository location: $KUBE_DIR"
echo ""
echo "Next steps:"
echo "  Run ocp-rebase.sh to perform a rebase:"
echo "  ./ocp-rebase.sh --k8s-tag=v1.35.0-alpha.2 --openshift-release=release-4.22"
echo ""
