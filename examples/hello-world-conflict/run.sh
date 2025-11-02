#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run setup first
echo "Setting up git repositories..."
bash "${SCRIPT_DIR}/setup.sh"

# Run convergence loop from fork directory
cd "${SCRIPT_DIR}/git-repos/fork"

echo ""
echo "Running Alphanso convergence loop..."
echo ""

alphanso run \
  --config "${SCRIPT_DIR}/config.yaml" \
  --verbose

echo ""
echo "✅ Example complete!"
echo ""
echo "Check the resolved conflict in:"
echo "   ${SCRIPT_DIR}/git-repos/fork/README.md"
