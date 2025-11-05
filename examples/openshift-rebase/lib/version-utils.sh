#!/usr/bin/env bash
# Version utility functions for handling Kubernetes versions, Go versions, and image tags

# Extract Go version from go.mod file
# Args:
#   $1: Path to go.mod file (optional, defaults to "go.mod")
# Returns:
#   Go version in format "1.23" (major.minor)
version_extract_go() {
  local go_mod_file="${1:-go.mod}"

  if [ ! -f "$go_mod_file" ]; then
    echo "Error: go.mod file not found: $go_mod_file" >&2
    return 1
  fi

  grep -E 'go 1\.[1-9][0-9]?' "$go_mod_file" \
    | sed -E 's/go (1\.[1-9][0-9]?).*/\1/' \
    | head -1 \
    | cut -d '.' -f 1,2
}

# Construct container image tag for OpenShift CI
# Args:
#   $1: Go version (e.g., "1.23")
#   $2: OpenShift release (e.g., "release-4.22")
# Returns:
#   Container image tag (e.g., "rhel-8-release-golang-1.23-openshift-4.22")
version_build_container_tag() {
  local go_version="$1"
  local openshift_release="$2"

  if [ -z "$go_version" ] || [ -z "$openshift_release" ]; then
    echo "Error: go_version and openshift_release required" >&2
    return 1
  fi

  # Strip "release-" prefix from openshift_release
  local release_num="${openshift_release#release-}"

  echo "rhel-8-release-golang-${go_version}-openshift-${release_num}"
}

# Update Kubernetes version in Dockerfile
# Args:
#   $1: Kubernetes tag (e.g., "v1.35.0-alpha.2")
#   $2: Path to Dockerfile
# Returns:
#   0 on success
version_update_dockerfile() {
  local k8s_tag="$1"
  local dockerfile="$2"

  if [ -z "$k8s_tag" ] || [ -z "$dockerfile" ]; then
    echo "Error: k8s_tag and dockerfile required" >&2
    return 1
  fi

  if [ ! -f "$dockerfile" ]; then
    echo "Error: Dockerfile not found: $dockerfile" >&2
    return 1
  fi

  # Strip leading 'v' from tag
  local version="${k8s_tag#v}"

  sed -i -E "s/(io.openshift.build.versions=\"kubernetes=)(1\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?)/\1${version}/" "$dockerfile"
}

# Update OpenShift dependencies in go.mod
# Args:
#   $1: OpenShift release (e.g., "release-4.22")
#   $2: Path to go.mod file (optional, defaults to "go.mod")
# Returns:
#   0 on success
version_update_gomod_deps() {
  local openshift_release="$1"
  local go_mod_file="${2:-go.mod}"

  if [ -z "$openshift_release" ]; then
    echo "Error: openshift_release required" >&2
    return 1
  fi

  if [ ! -f "$go_mod_file" ]; then
    echo "Error: go.mod file not found: $go_mod_file" >&2
    return 1
  fi

  sed -i -E "/=>/! s/(\\tgithub.com\\/openshift\\/[a-z|-]+) (.*)$/\\1 $openshift_release/" "$go_mod_file"
}

# Extract major.minor version from Kubernetes tag
# Args:
#   $1: Kubernetes tag (e.g., "v1.35.0-alpha.2")
# Returns:
#   Major.minor version (e.g., "1.35")
version_extract_k8s_major_minor() {
  local k8s_tag="$1"

  if [ -z "$k8s_tag" ]; then
    echo "Error: k8s_tag required" >&2
    return 1
  fi

  # Extract X.Y from vX.Y.Z format
  echo "$k8s_tag" | sed -E 's/v(1\.[0-9]+)\.[0-9]+.*/\1/'
}

# Build CHANGELOG URL for Kubernetes version
# Args:
#   $1: Kubernetes tag (e.g., "v1.35.0-alpha.2")
# Returns:
#   CHANGELOG URL
version_build_changelog_url() {
  local k8s_tag="$1"

  if [ -z "$k8s_tag" ]; then
    echo "Error: k8s_tag required" >&2
    return 1
  fi

  local xy_version=$(version_extract_k8s_major_minor "$k8s_tag")
  local version_slug=$(echo "$k8s_tag" | sed 's/\.//g')

  echo "https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-${xy_version}.md#${version_slug}"
}
