#!/usr/bin/env bash
# Git utility functions for repository operations and conflict management

# Check if all merge conflicts are resolved
# Returns:
#   0 if conflicts are resolved, non-zero otherwise
git_conflicts_resolved() {
  git diff --check &>/dev/null && ! git status | grep -q "Unmerged paths"
}

# Get list of conflicted files
# Returns:
#   List of conflicted file paths (one per line)
git_get_conflicted_files() {
  git status --porcelain | grep '^UU\|^AA\|^DD' || git diff --name-only --diff-filter=U
}

# Setup required git remotes for Kubernetes rebase
# Args:
#   None (assumes being run in repo directory)
# Returns:
#   0 on success
git_setup_remotes() {
  git remote add upstream git@github.com:kubernetes/kubernetes.git 2>/dev/null || true
  git remote add openshift git@github.com:openshift/kubernetes.git 2>/dev/null || true
  return 0
}

# Validate that origin is not pointing to upstream or openshift repos
# Returns:
#   0 if valid (personal fork), 1 if invalid (upstream/openshift)
git_validate_origin() {
  local origin
  origin=$(git remote get-url origin 2>/dev/null || echo "")

  if [[ -z "$origin" ]]; then
    return 1
  fi

  if [[ "$origin" =~ .*kubernetes/kubernetes.* ]] || [[ "$origin" =~ .*openshift/kubernetes.* ]]; then
    return 1
  fi

  return 0
}

# Fetch from upstream and openshift remotes
# Returns:
#   0 on success
git_fetch_remotes() {
  echo "Fetching from upstream and openshift..."
  git fetch upstream --tags -f
  git fetch openshift
}

# Pull from openshift release branch
# Args:
#   $1: OpenShift release branch (e.g., release-4.22)
# Returns:
#   0 on success
git_pull_openshift_release() {
  local openshift_release="$1"

  if [ -z "$openshift_release" ]; then
    echo "Error: openshift_release not specified"
    return 1
  fi

  echo "Pulling OpenShift release branch: $openshift_release"
  git pull openshift "$openshift_release"
}

# Attempt merge with upstream tag
# Args:
#   $1: Kubernetes tag (e.g., v1.35.0-alpha.2)
# Returns:
#   0 if merge succeeds, non-zero if conflicts
git_merge_upstream_tag() {
  local k8s_tag="$1"

  if [ -z "$k8s_tag" ]; then
    echo "Error: k8s_tag not specified"
    return 1
  fi

  echo ""
  echo "======================================================================"
  echo "Merging upstream Kubernetes $k8s_tag"
  echo "======================================================================"
  git merge "$k8s_tag"
}

# Clone a git repository
# Args:
#   $1: Repository URL
#   $2: Target directory
# Returns:
#   0 on success
git_clone_repo() {
  local repo_url="$1"
  local target_dir="$2"

  if [ -z "$repo_url" ] || [ -z "$target_dir" ]; then
    echo "Error: repo_url and target_dir required"
    return 1
  fi

  git clone "$repo_url" "$target_dir"
}

# Push to remote branch
# Args:
#   $1: Local branch
#   $2: Remote branch
# Returns:
#   0 on success
git_push_branch() {
  local local_branch="$1"
  local remote_branch="$2"

  if [ -z "$local_branch" ] || [ -z "$remote_branch" ]; then
    echo "Error: local_branch and remote_branch required"
    return 1
  fi

  git push origin "$local_branch:$remote_branch"
}
