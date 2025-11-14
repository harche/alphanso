# Dependabot Configuration Guide

This document explains the Dependabot configuration for Alphanso.

## Overview

Dependabot automatically checks for dependency updates and creates pull requests. Our configuration groups updates intelligently to reduce PR noise while maintaining security.

## Update Schedule

- **Frequency**: Weekly on Mondays at 09:00 UTC
- **Max Open PRs**: 5 for Python dependencies, 10 for GitHub Actions
- **Review Required**: All PRs require review before merging

## Grouped Updates

### 1. Core Dependencies
Updates grouped together for core runtime dependencies:
- `langgraph` - State graph orchestration
- `anthropic` - Claude API client
- `claude-agent-sdk` - Claude Agent SDK
- `pydantic` - Configuration validation

**Rationale**: These are tightly coupled and should be tested together.

### 2. Utilities
CLI and utility dependencies grouped together:
- `click` - CLI framework
- `rich` - Terminal formatting
- `pyyaml` - YAML parsing

**Rationale**: These are independent utilities with low risk of conflicts.

### 3. Development Dependencies
All dev tooling grouped together:
- Testing: `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`
- Type checking: `mypy`, `types-*`
- Formatting: `black`, `isort`, `ruff`
- Hooks: `pre-commit`

**Rationale**: Dev dependencies don't affect production and can be updated together.

### 4. Vertex AI Dependencies
Google Cloud dependencies for Vertex AI support:
- `google-cloud-aiplatform`
- Other `google-cloud-*` packages

**Rationale**: These are optional dependencies used together.

## Ignored Updates

### Major Version Updates

The following packages have major version updates **ignored** due to potential breaking changes:

1. **claude-agent-sdk**
   - Still in early development (0.x versions)
   - May have frequent breaking changes
   - Major updates require manual review and testing

2. **langgraph**
   - Complex state machine framework
   - Major updates may change API significantly
   - Requires careful migration testing

**Action Required**: Manually review and test major version updates before upgrading.

## Update Types

Dependabot will create PRs for:
- ✅ **Patch updates** (1.2.3 → 1.2.4) - Bug fixes
- ✅ **Minor updates** (1.2.3 → 1.3.0) - New features, backwards compatible
- ⚠️ **Major updates** (1.2.3 → 2.0.0) - Breaking changes (except ignored packages)

## PR Labels

All Dependabot PRs are automatically labeled:
- `dependencies` - All dependency updates
- `python` - Python package updates
- `github-actions` - GitHub Actions workflow updates

## Handling Dependabot PRs

### Automated Checks
Every PR triggers:
1. GitHub Actions CI (type checking, linting, tests)
2. Pre-commit hooks
3. Coverage reporting

### Review Process

1. **Check CI Status**
   - All tests must pass
   - Coverage must not decrease significantly

2. **Review Changes**
   - Read the changelog/release notes
   - Check for breaking changes
   - Review security advisories

3. **Test Locally** (for major updates)
   ```bash
   # Checkout the PR branch
   gh pr checkout <PR-number>

   # Sync dependencies
   uv sync --extra dev

   # Run tests
   uv run pytest -v

   # Run pre-commit
   uv run pre-commit run --all-files
   ```

4. **Merge Strategy**
   - Use "Squash and merge" for clean history
   - Keep the generated PR description
   - Add notes if manual changes were needed

### Grouped PRs

When Dependabot creates a grouped PR:
- Review all updates together
- Ensure no conflicts between versions
- Test the combination, not individual packages

## Security Updates

Dependabot also creates **security update PRs** for vulnerabilities:
- These are **not** affected by schedule - created immediately
- Labeled with `security`
- Should be reviewed and merged quickly

## Configuration Updates

To modify the Dependabot configuration:

1. Edit `.github/dependabot.yml`
2. Test configuration validity:
   ```bash
   # GitHub will validate on push
   git add .github/dependabot.yml
   git commit -m "chore: update dependabot config"
   git push
   ```
3. Check GitHub UI: Settings → Security → Dependabot

## Monitoring

View Dependabot activity:
- **Insights → Dependency graph → Dependabot**: See all open/closed PRs
- **Security → Dependabot alerts**: Security vulnerabilities
- **Pull requests**: Filter by `dependencies` label

## Troubleshooting

### Too Many PRs
- Reduce `open-pull-requests-limit`
- Increase grouping (add more patterns)
- Change schedule to less frequent

### Missing Updates
- Check that package ecosystem is correct (`pip` for Python)
- Verify `directory: "/"` is correct
- Check ignore rules aren't too broad

### Failed Updates
- Check CI logs in the PR
- May need to update constraints in `pyproject.toml`
- Consider if dependencies conflict with version pins

## Best Practices

1. **Don't ignore all PRs** - Review them weekly
2. **Merge security updates quickly** - Within 1-2 days
3. **Test grouped updates** - Don't assume all work together
4. **Keep CHANGELOG.md updated** - Note dependency updates in releases
5. **Monitor for breaking changes** - Read release notes

## Related Documentation

- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [TESTED_VERSIONS.md](../../TESTED_VERSIONS.md) - Known working versions
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development workflow
