#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/my-project"

# Setup if needed
if [ ! -d "${PROJECT_DIR}" ]; then
    echo "Setting up project..."
    bash "${SCRIPT_DIR}/setup.sh"
fi

echo ""
echo "============================================"
echo "Dependency Upgrade Example"
echo "============================================"
echo ""
echo "This will:"
echo "  1. Upgrade analytics from v1.0 to v2.0 (breaking changes)"
echo "  2. Run validators (will fail due to API changes)"
echo "  3. AI investigates failures and fixes code"
echo "  4. Re-run validators (should pass)"
echo ""
echo "Starting convergence loop..."
echo ""

# Run convergence from example directory
cd "${SCRIPT_DIR}"


uv run alphanso run --config config.yaml -vv 

echo ""
echo "============================================"
echo "✅ Upgrade Complete!"
echo "============================================"
echo ""
echo "Files modified by AI:"
echo "  - ${PROJECT_DIR}/src/main.py"
echo "  - ${PROJECT_DIR}/tests/test_main.py"
echo ""
echo "You can inspect the changes:"
echo "  cat ${PROJECT_DIR}/src/main.py"
echo ""
echo "Or re-run tests manually:"
echo "  cd ${PROJECT_DIR}"
echo "  source venv/bin/activate"
echo "  pytest tests/ -v"
