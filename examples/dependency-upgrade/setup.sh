#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/my-project"

echo "Creating dependency upgrade example..."

# Clean up any existing files
rm -rf "${PROJECT_DIR}" "${SCRIPT_DIR}/analytics-v1" "${SCRIPT_DIR}/analytics-v2"

# ============================================================================
# Create analytics v1.0.0 (old version with original API)
# ============================================================================
mkdir -p "${SCRIPT_DIR}/analytics-v1/analytics"

cat > "${SCRIPT_DIR}/analytics-v1/setup.py" <<'EOF'
from setuptools import setup, find_packages

setup(
    name="analytics",
    version="1.0.0",
    packages=find_packages(),
    description="Simple analytics library v1.0",
)
EOF

cat > "${SCRIPT_DIR}/analytics-v1/analytics/__init__.py" <<'EOF'
"""Analytics library v1.0 - Original API."""

class DataProcessor:
    """Process and analyze data (v1.0 API)."""

    def analyze(self, data):
        """Analyze data and return statistics as dict.

        Args:
            data: List of numbers

        Returns:
            dict with 'mean', 'count', 'sum' keys
        """
        return {
            'mean': sum(data) / len(data) if data else 0,
            'count': len(data),
            'sum': sum(data),
        }
EOF

# ============================================================================
# Create analytics v2.0.0 (new version with BREAKING changes)
# ============================================================================
mkdir -p "${SCRIPT_DIR}/analytics-v2/analytics/core"

cat > "${SCRIPT_DIR}/analytics-v2/setup.py" <<'EOF'
from setuptools import setup, find_packages

setup(
    name="analytics",
    version="2.0.0",
    packages=find_packages(),
    description="Analytics library v2.0 with breaking changes",
)
EOF

# Empty __init__ in analytics root
cat > "${SCRIPT_DIR}/analytics-v2/analytics/__init__.py" <<'EOF'
"""Analytics library v2.0 - Breaking changes!

BREAKING CHANGES from v1.0:
- DataProcessor moved to analytics.core.Analyzer
- Analyzer requires config parameter in constructor
- analyze() method renamed to process()
- Returns AnalysisResult object instead of dict
"""
EOF

cat > "${SCRIPT_DIR}/analytics-v2/analytics/core/__init__.py" <<'EOF'
"""Core analytics functionality (v2.0)."""

class Statistics:
    """Statistics container."""
    def __init__(self, mean, count, total):
        self.mean = mean
        self.count = count
        self.total = total

class AnalysisResult:
    """Result of data analysis (v2.0 API)."""
    def __init__(self, stats):
        self.statistics = Statistics(**stats)

class Analyzer:
    """Analyze data (v2.0 API - BREAKING CHANGES).

    Breaking changes from v1.0:
    - Requires config parameter in constructor
    - Use process() instead of analyze()
    - Returns AnalysisResult object instead of dict
    """

    def __init__(self, config):
        """Initialize analyzer with configuration.

        Args:
            config: dict with 'mode' key (required)
        """
        if not isinstance(config, dict) or 'mode' not in config:
            raise ValueError("config must be dict with 'mode' key")
        self.config = config

    def process(self, data):
        """Process data and return analysis result.

        Args:
            data: List of numbers

        Returns:
            AnalysisResult object with .statistics attribute
        """
        stats = {
            'mean': sum(data) / len(data) if data else 0,
            'count': len(data),
            'total': sum(data),
        }
        return AnalysisResult(stats)
EOF

# ============================================================================
# Create sample project using analytics v1.0
# ============================================================================
mkdir -p "${PROJECT_DIR}"/{src,tests}

cat > "${PROJECT_DIR}/requirements.txt" <<'EOF'
pytest>=7.0.0
EOF

cat > "${PROJECT_DIR}/src/__init__.py" <<'EOF'
"""Sample project using analytics library."""
EOF

cat > "${PROJECT_DIR}/src/main.py" <<'EOF'
"""Main module demonstrating analytics library usage (v1.0 API)."""

from analytics import DataProcessor


def calculate_metrics(data):
    """Calculate metrics for given data.

    Args:
        data: List of numbers

    Returns:
        dict with calculated metrics
    """
    processor = DataProcessor()
    result = processor.analyze(data)
    return result


def main():
    """Main function."""
    data = [10, 20, 30, 40, 50]

    result = calculate_metrics(data)

    print(f"Data: {data}")
    print(f"Mean: {result['mean']}")
    print(f"Count: {result['count']}")
    print(f"Sum: {result['sum']}")

    return result


if __name__ == "__main__":
    main()
EOF

cat > "${PROJECT_DIR}/tests/test_main.py" <<'EOF'
"""Tests for main module (using v1.0 API)."""

from src.main import calculate_metrics, main


def test_calculate_metrics():
    """Test calculate_metrics function."""
    data = [10, 20, 30, 40, 50]
    result = calculate_metrics(data)

    assert result['mean'] == 30.0
    assert result['count'] == 5
    assert result['sum'] == 150


def test_main():
    """Test main function."""
    result = main()

    assert result['mean'] == 30.0
    assert result['count'] == 5
    assert result['sum'] == 150
EOF

# ============================================================================
# Setup virtual environment and install v1.0
# ============================================================================
cd "${PROJECT_DIR}"

echo ""
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q pytest
pip install -q -e "${SCRIPT_DIR}/analytics-v1"

echo ""
echo "Testing with analytics v1.0..."
python -m pytest tests/ -v --override-ini="addopts="

echo ""
echo "✅ Project created successfully!"
echo ""
echo "Project structure:"
echo "  - analytics-v1/     Old dependency (v1.0.0)"
echo "  - analytics-v2/     New dependency (v2.0.0) with breaking changes"
echo "  - my-project/       Sample project using v1.0 API"
echo ""
echo "Breaking changes in v2.0:"
echo "  1. Module moved: analytics → analytics.core"
echo "  2. Class renamed: DataProcessor → Analyzer"
echo "  3. Constructor requires config: Analyzer(config={'mode': 'fast'})"
echo "  4. Method renamed: .analyze() → .process()"
echo "  5. Return type changed: dict → AnalysisResult object"
echo "  6. Data access changed: result['key'] → result.statistics.key"
echo ""
echo "Run ./run.sh to upgrade to v2.0 and let AI fix the breaking changes!"
