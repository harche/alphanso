#!/bin/bash

# CI Image Setup Functions
# This library provides functions to create custom CI build images for OpenShift CI
# when the standard images don't have the required Go version.
#
# IMPORTANT LIMITATION:
# The repository's .ci-operator.yaml file can only reference existing image stream tags
# when the central config uses "from_repository: true". It cannot define custom Dockerfiles
# via "project_image" - that must be done in the central config at openshift/release repo.
#
# Therefore, these functions are currently not used automatically. They're kept for reference
# and for manually creating Dockerfiles that could be added to openshift/release.

# Creates a custom Dockerfile for OpenShift CI builds
# This Dockerfile matches the container setup used by the rebaser tool
create_ci_dockerfile() {
  local dockerfile_path="$1"
  local go_version="$2"

  # Extract major.minor version (e.g., "1.25.3" -> "1.25")
  local go_major_minor="${go_version%.*}"

  mkdir -p "$(dirname "$dockerfile_path")"

  cat > "$dockerfile_path" <<EOF
# Custom CI build root for Kubernetes builds requiring Go ${go_major_minor}+
# Uses Debian Bookworm for glibc 2.36 (required for protobuf code generation)
# This matches the build environment used by the rebaser tool

FROM golang:${go_major_minor}-bookworm

# Install build dependencies
RUN apt-get update -qq && \
    apt-get install -y -qq \
      jq \
      unzip \
      wget \
      iproute2 \
      rsync \
      git \
      make \
    && rm -rf /var/lib/apt/lists/*

# Install protoc 23.4 (required for code generation)
RUN wget -q https://github.com/protocolbuffers/protobuf/releases/download/v23.4/protoc-23.4-linux-x86_64.zip && \
    unzip -q protoc-23.4-linux-x86_64.zip -d /usr/local && \
    rm protoc-23.4-linux-x86_64.zip

# Set working directory
WORKDIR /go/src/k8s.io/kubernetes

# Note: etcd will be installed by hack/install-etcd.sh during build
EOF

  echo "Created CI Dockerfile at: $dockerfile_path"
}

# Updates .ci-operator.yaml to use custom project_image instead of build_root_image
update_ci_operator_yaml() {
  local ci_operator_file="$1"
  local dockerfile_path="$2"

  if [ ! -f "$ci_operator_file" ]; then
    echo "Error: .ci-operator.yaml not found at $ci_operator_file"
    return 1
  fi

  # Backup original file
  cp "$ci_operator_file" "${ci_operator_file}.bak"

  # Replace build_root_image with build_root using project_image
  cat > "$ci_operator_file" <<EOF
build_root:
  project_image:
    dockerfile_path: $dockerfile_path
EOF

  echo "Updated .ci-operator.yaml to use custom Dockerfile"
  echo "Backup saved at: ${ci_operator_file}.bak"
}

# Main function to setup CI custom image
# Call this after a successful rebase when Go version is too new for OpenShift CI
setup_custom_ci_image() {
  local kube_dir="$1"
  local go_version="$2"

  echo "Setting up custom CI build image..."

  local dockerfile_path="openshift-hack/images/ci-build-root/Dockerfile"
  local ci_operator_file="$kube_dir/.ci-operator.yaml"

  # Create the Dockerfile
  create_ci_dockerfile "$kube_dir/$dockerfile_path" "$go_version"

  # Update .ci-operator.yaml
  update_ci_operator_yaml "$ci_operator_file" "$dockerfile_path"

  echo ""
  echo "✓ Custom CI image configuration complete"
  echo "  - Dockerfile: $dockerfile_path"
  echo "  - Configuration: .ci-operator.yaml"
  echo ""
  echo "These files will be included in your rebase PR so OpenShift CI can build"
  echo "using Go $go_version even though the standard CI images only have Go 1.24."
}
