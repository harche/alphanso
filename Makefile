.PHONY: help install dev-install install-vertex test test-verbose test-coverage lint format format-check typecheck clean clean-all check ci

# Default target - show help
help:
	@echo "Alphanso Development Makefile"
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all tests quickly"
	@echo "  make test-verbose      - Run tests with verbose output"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              - Run ruff linter"
	@echo "  make format            - Auto-format code with black and isort"
	@echo "  make format-check      - Check formatting without modifying"
	@echo "  make typecheck         - Run mypy type checker"
	@echo "  make check             - Run all checks (lint + typecheck + format-check)"
	@echo ""
	@echo "Installation:"
	@echo "  make install           - Install package (production)"
	@echo "  make dev-install       - Install with dev dependencies"
	@echo "  make install-vertex    - Install with Vertex AI support"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             - Remove cache and build artifacts"
	@echo "  make clean-all         - Deep clean (including .venv)"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci                - Run full CI pipeline (check + test-coverage)"

# Testing targets
test:
	@echo "Running tests..."
	uv run pytest -v --no-cov

test-verbose:
	@echo "Running tests with verbose output..."
	uv run pytest -vv

test-coverage:
	@echo "Running tests with coverage..."
	uv run pytest -v --cov=alphanso --cov-report=term-missing --cov-report=html --cov-report=xml

# Code quality targets
lint:
	@echo "Running ruff linter..."
	uv run ruff check src tests

format:
	@echo "Formatting code with black..."
	uv run black src tests
	@echo "Sorting imports with isort..."
	uv run isort src tests

format-check:
	@echo "Checking code formatting..."
	uv run black --check src tests
	uv run isort --check-only src tests

typecheck:
	@echo "Running mypy type checker..."
	uv run mypy src

# Installation targets
install:
	@echo "Installing package..."
	uv pip install .

dev-install:
	@echo "Installing with dev dependencies..."
	uv pip install -e ".[dev]"

install-vertex:
	@echo "Installing with Vertex AI support..."
	uv pip install -e ".[dev,vertex]"

# Maintenance targets
clean:
	@echo "Cleaning cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ .eggs/ 2>/dev/null || true
	rm -rf .pytest_cache/ .coverage htmlcov/ coverage.xml 2>/dev/null || true
	rm -rf .mypy_cache/ .ruff_cache/ 2>/dev/null || true
	@echo "Clean complete!"

clean-all: clean
	@echo "Deep cleaning (including .venv)..."
	rm -rf .venv/
	@echo "Deep clean complete!"

# Combined targets
check: format-check lint typecheck
	@echo "All checks passed!"

ci: check test-coverage
	@echo "CI pipeline complete!"
