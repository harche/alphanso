# Contributing to Alphanso

Thank you for your interest in contributing to Alphanso! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/alphanso.git
   cd alphanso
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/harche/alphanso.git
   ```

## Development Setup

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Git

### Install Dependencies

```bash
# Install all dependencies including dev tools
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

### API Keys for Testing

For integration tests, you'll need either:

**Option 1: Anthropic API**
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

**Option 2: Google Vertex AI**
```bash
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION="your-region"
export ANTHROPIC_VERTEX_PROJECT_ID="your-project-id"
gcloud auth application-default login
```

## Making Changes

### Branching Strategy

- `main` - Stable release branch
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Creating a Feature Branch

```bash
# Update your local main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**
```bash
git commit -m "feat(validators): add timeout support for test suite validator"
git commit -m "fix(agent): handle None content in tool results"
git commit -m "docs(readme): update security best practices"
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest -v --cov=src/alphanso --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_validators.py -v

# Run specific test
uv run pytest tests/unit/test_validators.py::TestCommandValidator::test_successful_command -v
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Mock external dependencies (API calls, file system operations)
- Aim for >80% code coverage

**Example test structure:**
```python
class TestMyFeature:
    """Tests for MyFeature class."""

    def test_feature_with_valid_input(self) -> None:
        """Test that feature works with valid input."""
        # Arrange
        feature = MyFeature()

        # Act
        result = feature.process("valid input")

        # Assert
        assert result.success is True
        assert result.output == "expected output"

    @pytest.mark.asyncio
    async def test_async_feature(self) -> None:
        """Test async feature behavior."""
        feature = MyFeature()
        result = await feature.aprocess("input")
        assert result is not None
```

## Code Quality

### Type Checking

```bash
# Run mypy on source code
uv run mypy src/alphanso

# Run mypy on tests
uv run mypy tests/
```

All code must pass type checking with no errors.

### Code Formatting

We use:
- **black** for code formatting (line length: 100)
- **isort** for import sorting
- **ruff** for linting

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Lint
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check src/ tests/ --fix
```

### Pre-commit Hooks

Pre-commit hooks automatically run formatters and linters:

```bash
# Install hooks
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

Hooks will run automatically on `git commit`.

## Submitting Changes

### Pull Request Process

1. **Update your branch**:
   ```bash
   git checkout main
   git pull upstream main
   git checkout feature/your-feature
   git rebase main
   ```

2. **Ensure all checks pass**:
   ```bash
   # Run tests
   uv run pytest -v

   # Run type checking
   uv run mypy src/alphanso

   # Run linting
   uv run ruff check src/ tests/

   # Run formatters
   uv run black src/ tests/
   uv run isort src/ tests/
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature
   ```

4. **Create Pull Request** on GitHub:
   - Use a descriptive title
   - Reference any related issues
   - Describe your changes
   - Include examples if applicable

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] Code is formatted (black, isort)
- [ ] Linting passes (ruff)
- [ ] Type checking passes (mypy)
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Commit messages follow conventions

## Release Process

Releases are managed by maintainers. The process includes:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with release date
3. Create git tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
4. Push tag: `git push upstream v0.2.0`
5. GitHub Actions will create the release

## Code Review Guidelines

Reviewers will check for:
- Code quality and clarity
- Test coverage
- Documentation
- Performance implications
- Security considerations
- Backwards compatibility

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Alphanso! 🎉
