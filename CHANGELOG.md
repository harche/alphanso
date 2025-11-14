# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive security documentation in README
- Tested version combinations documentation (TESTED_VERSIONS.md)
- Pre-commit hooks for code quality
- GitHub Actions CI workflow for automated testing
- CONTRIBUTING.md with contribution guidelines

### Changed
- Improved test coverage for agent/client.py from 24.72% to 91.01%
- Updated version pinning to use major version constraints
- Overall project coverage improved to 87.86%

### Fixed
- Fixed 5 mypy type errors in src/ directory
- Fixed bare except clause in validators/git.py
- Fixed all ruff linting errors (49 total)

## [0.1.0] - 2025-01-14

### Added
- Initial release of Alphanso framework
- LangGraph-based convergence loop architecture
- Claude Agent SDK integration with bypassPermissions mode
- Support for pre-actions (one-time setup)
- Main script execution with retry logic
- Validator framework with command and git conflict validators
- Test suite validator for running test commands
- AI-powered fixing with Claude
- Async API for embedding in async applications
- CLI interface with rich logging
- Configuration system with Pydantic validation
- Support for both Anthropic API and Google Vertex AI
- Examples:
  - Hello World (git merge conflict resolution)
  - OpenShift Rebase (complex Kubernetes fork rebasing)
  - Dependency Upgrade (automated dependency updates)

### Documentation
- Comprehensive README with usage examples
- Workflow architecture diagrams
- Quick start guide
- API documentation for async usage
- Security documentation with threat model
- Development setup instructions

### Testing
- 195 unit and integration tests
- 87.86% code coverage
- Pytest with async support
- Mock-based testing for agent client
- Integration tests for validators

### Infrastructure
- Python 3.13+ support
- UV-based dependency management
- Type checking with mypy
- Code formatting with black and isort
- Linting with ruff
- Coverage reporting

[Unreleased]: https://github.com/harche/alphanso/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/harche/alphanso/releases/tag/v0.1.0
