#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/kubernetes"



# Run convergence from example directory
cd "${SCRIPT_DIR}"


uv run alphanso run --config config.yaml
