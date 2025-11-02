#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run setup first
echo "Setting up git repositories..."
bash "${SCRIPT_DIR}/setup.sh"

# Run convergence loop from example directory
echo ""
echo "Running Alphanso convergence loop..."
echo ""

# Run from the example directory (config uses relative path to git-repos/fork)
cd "${SCRIPT_DIR}"
uv run alphanso run \
  --config config.yaml

echo ""
echo "✅ Example complete!"
echo ""
echo "Check the resolved conflict in:"
echo "   ${SCRIPT_DIR}/git-repos/fork/README.md"
