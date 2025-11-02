#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_DIR="${SCRIPT_DIR}/git-repos"

# Clean up any existing repos
rm -rf "${REPOS_DIR}"
mkdir -p "${REPOS_DIR}"

echo "Creating git repositories with merge conflict..."

# Create upstream repo
cd "${REPOS_DIR}"
mkdir upstream
cd upstream
git init
git config user.name "Upstream Dev"
git config user.email "upstream@example.com"

# Create initial file
cat > README.md <<'EOF'
# Hello World Project

Version: 1.0.0

## Features
- Feature A
- Feature B
EOF

git add README.md
git commit -m "Initial commit"
git tag v1.0.0

# Modify in upstream (version 2.0.0)
cat > README.md <<'EOF'
# Hello World Project

Version: 2.0.0

## Features
- Feature A (enhanced)
- Feature B (enhanced)
- Feature C (new)
EOF

git add README.md
git commit -m "Update to v2.0.0"
git tag v2.0.0

# Create fork repo
cd "${REPOS_DIR}"
git clone upstream fork
cd fork
git config user.name "Fork Dev"
git config user.email "fork@example.com"

# Make conflicting changes in fork
cat > README.md <<'EOF'
# Hello World Project - Forked Edition

Version: 1.0.0-fork

## Features
- Feature A (fork-specific)
- Feature B (fork-specific)
- Feature D (fork-only)
EOF

git add README.md
git commit -m "Fork-specific changes"

# Add upstream as remote (use absolute path so it works from any directory)
git remote add upstream "${REPOS_DIR}/upstream"

echo ""
echo "✅ Git repositories created:"
echo "   - Upstream: ${REPOS_DIR}/upstream (v2.0.0)"
echo "   - Fork: ${REPOS_DIR}/fork (with conflicting changes)"
echo ""
echo "To create the conflict, run:"
echo "   cd ${REPOS_DIR}/fork"
echo "   git fetch upstream"
echo "   git merge v2.0.0  # This will create a merge conflict"
