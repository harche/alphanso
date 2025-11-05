#!/bin/bash

# OpenShift Kubernetes Rebase Tool
#
# This tool helps rebase OpenShift's Kubernetes fork against upstream Kubernetes releases.
# Assumes the repository has been set up using setup.sh
#
# Requirements: jq, git, podman, bash
# Optional: gh (GitHub CLI) for creating pull requests
#
# IMPORTANT: Run setup.sh first to clone the repository and configure remotes.

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Allow override for testing
KUBE_DIR="${REBASER_KUBE_DIR:-${SCRIPT_DIR}/kubernetes}"

# Source helper libraries
source "${SCRIPT_DIR}/lib/auto-merge.sh"
source "${SCRIPT_DIR}/lib/ci-image-setup.sh"

# Arguments
k8s_tag=""
openshift_release=""
bugzilla_id=""
cleanup_mode=false
auto_merge=false

usage() {
  echo "OpenShift Kubernetes Rebase Tool"
  echo ""
  echo "IMPORTANT: Run setup.sh first to clone the repository and configure remotes."
  echo ""
  echo "Usage: $0 [options]"
  echo ""
  echo "Required arguments:"
  echo "  --k8s-tag=<tag>              Upstream Kubernetes tag (e.g., v1.35.0-alpha.2)"
  echo "  --openshift-release=<branch> OpenShift release branch (e.g., release-4.22)"
  echo ""
  echo "Optional arguments:"
  echo "  --bugzilla-id=<id>           Bugzilla ID for PR creation (e.g., 2003027)"
  echo "  --auto-merge                 Enable automated conflict resolution with Claude Code"
  echo "  --cleanup                    Clean up from previous rebase attempt and exit"
  echo ""
  echo "Examples:"
  echo "  # Basic rebase:"
  echo "  $0 --k8s-tag=v1.35.0-alpha.2 --openshift-release=release-4.22"
  echo ""
  echo "  # With automated conflict resolution:"
  echo "  $0 --k8s-tag=v1.35.0-alpha.2 --openshift-release=release-4.22 --auto-merge"
  echo ""
  echo "  # Cleanup after failed rebase:"
  echo "  $0 --cleanup"
}

cleanup_rebase() {
  echo "======================================================================"
  echo "Cleaning up from previous rebase attempt..."
  echo "======================================================================"

  if [ ! -d "$KUBE_DIR" ]; then
    echo "No kubernetes directory found - nothing to clean up."
    echo "Ready for next rebase attempt."
    exit 0
  fi

  echo "Removing kubernetes directory: $KUBE_DIR"
  rm -rf "$KUBE_DIR"

  if [ -d "$KUBE_DIR" ]; then
    echo "Error: Failed to remove kubernetes directory"
    exit 1
  fi

  echo ""
  echo "✓ Cleanup complete!"
  echo "Ready for next rebase attempt (will clone fresh on next run)."
  exit 0
}

# Parse arguments
for i in "$@"; do
  case $i in
    --k8s-tag=*)
      k8s_tag="${i#*=}"
      shift
      ;;
    --openshift-release=*)
      openshift_release="${i#*=}"
      shift
      ;;
    --bugzilla-id=*)
      bugzilla_id="${i#*=}"
      shift
      ;;
    --auto-merge)
      auto_merge=true
      shift
      ;;
    --cleanup)
      cleanup_mode=true
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

# Handle cleanup mode
if [ "$cleanup_mode" = true ]; then
  cleanup_rebase
fi

# Validate required arguments
if [ -z "$k8s_tag" ]; then
  echo "Error: Required argument missing: --k8s-tag"
  echo ""
  usage
  exit 1
fi

if [ -z "$openshift_release" ]; then
  echo "Error: Required argument missing: --openshift-release"
  echo ""
  usage
  exit 1
fi

# Check if kubernetes directory exists
if [ ! -d "$KUBE_DIR" ]; then
  echo "Error: Kubernetes repository not found at: $KUBE_DIR"
  echo ""
  echo "Please run setup.sh first to clone the repository and configure remotes:"
  echo "  ./setup.sh --fork-repo=<your-fork-url>"
  echo ""
  exit 1
fi

# Change to kubernetes directory
cd "$KUBE_DIR"

echo "======================================================================"
echo "OpenShift Kubernetes Rebase"
echo "======================================================================"
echo "Kubernetes tag: $k8s_tag"
echo "OpenShift release: $openshift_release"
[ -n "$bugzilla_id" ] && echo "Bugzilla ID: $bugzilla_id"
echo "Auto-merge: $auto_merge"
echo "Working directory: $PWD"
echo ""

# Check prerequisites
for cmd in git jq podman; do
  if ! command -v $cmd &>/dev/null; then
    echo "Error: $cmd not installed"
    exit 1
  fi
done

# Verify remotes are configured (should have been done by setup.sh)
if ! git remote | grep -q "^upstream$" || ! git remote | grep -q "^openshift$"; then
  echo "Error: Git remotes not configured properly"
  echo ""
  echo "Please run setup.sh first to configure remotes:"
  echo "  ./setup.sh --fork-repo=<your-fork-url>"
  echo ""
  exit 1
fi

# Fetch latest changes
echo "Fetching from upstream and openshift..."
git fetch upstream --tags -f
git fetch openshift

# Pull the OpenShift release branch
echo "Pulling OpenShift release branch: $openshift_release"
git pull --ff-only openshift "$openshift_release"

# Determine required Go version from .go-version file
# Kubernetes v1.35+ requires Go 1.25, but OpenShift CI images only have up to Go 1.24
required_go_version=""
if [ -f .go-version ]; then
  required_go_version=$(cat .go-version | tr -d '[:space:]')
  echo "Required Go version (from .go-version): $required_go_version"
fi

# Determine container image tag from OpenShift's CI configuration
# This is more reliable than constructing it, as OpenShift controls the available tags
use_openshift_image=true
if [ -f .ci-operator.yaml ]; then
  tag=$(grep -A 3 'build_root_image:' .ci-operator.yaml | grep 'tag:' | awk '{print $2}')
  echo "Container image tag (from .ci-operator.yaml): $tag"

  # Check if OpenShift image has insufficient Go version
  # OpenShift images only have Go 1.24 as of now, but Kubernetes v1.35+ requires Go 1.25+
  if [ -n "$required_go_version" ] && [[ "$required_go_version" > "1.24" ]]; then
    echo "WARNING: Required Go $required_go_version but OpenShift image only has Go 1.24"
    echo "Falling back to upstream Kubernetes kube-cross image as workaround"
    use_openshift_image=false
  fi
else
  # Fallback to constructing the tag (for older repos or when .ci-operator.yaml doesn't exist)
  go_mod_go_ver=$(grep -E 'go 1\.[1-9][0-9]?' go.mod | sed -E 's/go (1\.[1-9][0-9]?)/\1/' | cut -d '.' -f 1,2)
  tag="rhel-8-release-golang-${go_mod_go_ver}-openshift-${openshift_release#release-}"
  echo "Container image tag (constructed): $tag"
fi

# Set container image and runtime based on availability
# TODO: Switch back to OpenShift image when Go 1.25+ becomes available in registry.ci.openshift.org
if [ "$use_openshift_image" = true ]; then
  container_image="registry.ci.openshift.org/openshift/release:$tag"
else
  # Use golang:1.25-bookworm as fallback when OpenShift image lacks required Go version
  # Bookworm has glibc 2.36 (vs Bullseye's 2.31), which is required for code generation tools
  # This solves the "GLIBC_2.34 not found" error we get with kube-cross:bullseye
  # TODO: Switch to kube-cross:bookworm when upstream provides it
  container_image="golang:1.25-bookworm"
  echo "Using golang:1.25-bookworm (glibc 2.36, Go 1.25)"
fi

# SELinux relabeling is needed on SELinux-enabled hosts regardless of container base image
# Use :Z for private unshared content
selinux_flag=":Z"
container_runtime="podman"

echo "Using container image: $container_image"

# Export container image info for auto-merge to use
export REBASER_CONTAINER_IMAGE="$container_image"
export REBASER_CONTAINER_RUNTIME="$container_runtime"
export REBASER_SELINUX_FLAG="$selinux_flag"

# Attempt merge with upstream
echo ""
echo "======================================================================"
echo "Merging upstream Kubernetes $k8s_tag"
echo "======================================================================"

# Capture exit code without triggering set -e
set +e
git merge "$k8s_tag"
merge_exit_code=$?
set -e

if [ $merge_exit_code -eq 0 ]; then
  echo "✓ No conflicts detected. Automatic merge succeeded"

  # If auto-merge is enabled, use the retry loop for container operations
  # This allows Claude to fix any build/generation errors
  if [ "$auto_merge" = true ]; then
    echo ""
    echo "Invoking automated build process with retry capability..."
    auto_merge_conflicts "$openshift_release" "$k8s_tag"
  else
    # Manual mode: run container operations once and exit on failure
    if [ -z "${REBASER_SKIP_CONTAINER_OPS:-}" ]; then
      echo ""
      echo "======================================================================"
      echo "Running container operations (go mod tidy, hack/update-vendor.sh, make update)..."
      echo "======================================================================"

      # Determine setup commands based on container image
      setup_cmd=""
      if [[ "$container_image" == "golang:"* ]]; then
        setup_cmd="apt-get update -qq && apt-get install -y -qq jq unzip wget && \
wget -q https://github.com/protocolbuffers/protobuf/releases/download/v23.4/protoc-23.4-linux-x86_64.zip && \
unzip -q protoc-23.4-linux-x86_64.zip -d /usr/local && \
rm protoc-23.4-linux-x86_64.zip && "
      fi

      if ! $container_runtime run -it --rm -v "$(pwd):/go/k8s.io/kubernetes${selinux_flag}" \
        --workdir=/go/k8s.io/kubernetes \
        "$container_image" \
        bash -c "${setup_cmd}go mod tidy && hack/update-vendor.sh && make update"; then
        echo ""
        echo "Error: Container operations failed"
        echo "Please fix the errors and re-run the script"
        exit 1
      fi
    fi
  fi
else
  # Handle conflicts - exit with error
  echo ""
  echo "Error: Merge conflicts detected during rebase of $k8s_tag"
  echo ""
  git status
  echo ""
  exit 1
fi

# Update version in Dockerfile
echo ""
echo "Updating Dockerfile version..."
sed -i -E "s/(io.openshift.build.versions=\"kubernetes=)(1\.[0-9]+\.[0-9]+)/\1${k8s_tag:1}/" openshift-hack/images/hyperkube/Dockerfile.rhel

# Update OpenShift go.mod dependencies
echo "Updating OpenShift go.mod dependencies..."
sed -i -E "/=>/! s/(\tgithub.com\/openshift\/[a-z|-]+) (.*)$/\1 $openshift_release/" go.mod

# Container operations (go mod tidy, hack/update-vendor.sh, make update) are now handled
# by the auto-merge retry loop. They will run after conflict resolution and retry on failure.
# For manual rebases (without --auto-merge), user needs to run these manually.

# Commit vendor and generated files if there were conflicts handled by auto-merge
# (auto-merge stages files but doesn't commit, so we commit here)
echo ""
if [ "$auto_merge" = true ] && ! git diff-index --quiet HEAD --; then
  echo "Committing changes from auto-merge resolution..."
  git add -A
  git commit -m "UPSTREAM: <drop>: resolve conflicts and update generated files"
elif [ "$auto_merge" = false ]; then
  # For manual rebases, commit any staged changes
  echo "Committing manually resolved changes..."
  git add -A
  if ! git diff-index --quiet HEAD --; then
    git commit -m "UPSTREAM: <drop>: manually resolve conflicts"
  else
    echo "No changes to commit"
  fi
fi

# TODO: Setup custom CI build image if using newer Go version than OpenShift CI supports
# NOTE: This requires updating the central config in openshift/release repo,
# not the repository's .ci-operator.yaml file. The .ci-operator.yaml can only
# reference existing image stream tags when using from_repository: true.
# For now, CI will fail with Go version mismatches until OpenShift updates
# their build images or we create a PR to openshift/release.
#
# if [ -n "$required_go_version" ] && [[ "$required_go_version" > "1.24" ]]; then
#   echo ""
#   echo "======================================================================"
#   echo "WARNING: Go $required_go_version required but OpenShift CI only has Go 1.24"
#   echo "======================================================================"
#   echo "CI jobs will fail until OpenShift updates their build images."
#   echo "To fix this, a PR to openshift/release repo is needed to add project_image"
#   echo "to the central ci-operator config for openshift/kubernetes."
# fi

# Push to remote
remote_branch="rebase-$k8s_tag"
echo ""
echo "======================================================================"
echo "Pushing to remote branch: $remote_branch"
echo "======================================================================"
git push origin "HEAD:$remote_branch"

# Create PR if bugzilla ID provided
if [ -n "$bugzilla_id" ]; then
  if command -v gh &>/dev/null; then
    XY=$(echo "$k8s_tag" | sed -E "s/v(1\.[0-9]+)\.[0-9]+/\1/")
    ver=$(echo "$k8s_tag" | sed "s/\.//g")
    link="https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-$XY.md#$ver"

    echo ""
    echo "Creating pull request..."
    gh pr create \
      --title "Bug $bugzilla_id: Rebase $k8s_tag" \
      --body "CHANGELOG $link" \
      --web
  else
    echo ""
    echo "GitHub CLI (gh) not found. Skipping PR creation."
    echo "Install gh to enable automatic PR creation."
  fi
fi

echo ""
echo "======================================================================"
echo "✓ Rebase complete!"
echo "======================================================================"
echo "Branch: $remote_branch"
echo "Next steps:"
echo "  1. Review the changes pushed to $remote_branch"
if [ -z "$bugzilla_id" ]; then
  echo "  2. Create a pull request manually if needed"
fi
echo ""
