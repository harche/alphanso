# Pull Request Commands and Auto-Merge

This document describes the automated PR management features available in this repository.

## Auto-Merge for PRs

### Dependabot PRs

**⚠️ SECURITY: Only Dependabot PRs are auto-merged automatically.**

Dependabot PRs are automatically approved and merged when:
- ✅ PR author is `dependabot[bot]` (verified)
- ✅ All CI checks pass
- ✅ Update is minor or patch version (not major)
- ✅ No manual holds are placed
- ✅ Branch protection rules satisfied

### External Contributor PRs

**⚠️ SECURITY: External PRs require BOTH approval AND lgtm from @harche (repository owner).**

External contributor PRs are auto-merged when:
- ✅ PR is NOT from `harche` or `dependabot[bot]`
- ✅ PR has approval review from @harche (via `/approve`)
- ✅ PR has `lgtm` label from @harche (via `/lgtm`)
- ✅ All CI checks pass
- ✅ No merge conflicts
- ✅ Branch protection rules satisfied

### Dependabot Workflow

1. Dependabot opens a PR
2. CI runs automatically
3. If checks pass and it's not a major update:
   - PR is auto-approved
   - Auto-merge is enabled
   - PR merges automatically when all conditions met

**Major version updates** require manual review and are NOT auto-merged.

### External Contributor Workflow

1. External contributor opens a PR
2. CI runs automatically
3. Repository owner (@harche) reviews the PR
4. Owner comments `/approve` to approve the PR
5. Owner comments `/lgtm` to add lgtm label
6. Auto-merge workflow detects both conditions
7. Auto-merge is enabled
8. PR merges automatically when all CI checks pass

**Security:** See [AUTO_MERGE_SECURITY.md](./AUTO_MERGE_SECURITY.md) for detailed security controls.

## PR Slash Commands

**⚠️ SECURITY: Only maintainers, collaborators, and org members can use PR commands. External contributors are silently ignored.**

Comment on any PR with these commands to trigger actions:

### Hold Commands

**`/hold`**
- Puts PR on hold
- Adds `do-not-merge/hold` label
- Prevents auto-merge
- Use when PR needs discussion or is not ready

**`/unhold`**
- Removes hold
- Removes `do-not-merge/hold` label
- Re-enables auto-merge (if configured)

Example:
```
/hold
```
Response: 🚧 PR is on hold. Use `/unhold` to remove the hold.

### Approval Commands

**`/approve`**
- Approves the PR
- Adds GitHub approval review

**`/lgtm`**
- Approves the PR
- Adds `lgtm` (Looks Good To Me) label
- Indicates PR is ready to merge

### Merge Commands

**`/merge`**
- Merges the PR immediately
- Requires:
  - At least one approval
  - All checks passing
- Uses squash merge strategy

### Testing Commands

**`/retest`**
- Provides instructions to retrigger CI
- Useful when tests fail due to transient issues

### Help Command

**`/help`**
- Shows list of all available commands
- Includes both slash commands and Dependabot commands

## Dependabot Commands

These are built-in Dependabot commands (mention `@dependabot`):

**`@dependabot rebase`**
- Rebases PR on latest main branch
- Triggers CI re-run

**`@dependabot recreate`**
- Closes and recreates the PR from scratch
- Useful if PR is in a bad state

**`@dependabot merge`**
- Merges the PR (if all checks pass)
- Uses default merge strategy

**`@dependabot squash and merge`**
- Squashes commits and merges
- Cleaner commit history

**`@dependabot close`**
- Closes the PR without merging

**`@dependabot reopen`**
- Reopens a closed PR

**`@dependabot ignore this [dependency|version|major|minor|patch]`**
- Ignores specific updates
- Examples:
  - `@dependabot ignore this major version`
  - `@dependabot ignore this dependency`

## Labels

### Auto-Applied Labels

- `dependencies` - All dependency updates
- `python` - Python package updates
- `github-actions` - GitHub Actions updates

### Command Labels

- `do-not-merge/hold` - Applied by `/hold`, prevents merge
- `lgtm` - Applied by `/lgtm`, indicates approval
- `WIP` - Work in Progress, manually applied

## Workflow Details

### Dependabot Auto-Merge Workflow

**File:** `.github/workflows/dependabot-auto-merge.yml`

**Triggers:** When Dependabot opens/updates a PR

**Jobs:**
1. **auto-approve**: Approves non-major updates
2. **auto-merge**: Enables auto-merge after approval

**Permissions Required:**
- `contents: write` - To merge PRs
- `pull-requests: write` - To approve and merge

### PR Commands Workflow

**File:** `.github/workflows/pr-commands.yml`

**Triggers:** When someone comments on a PR

**Supported Commands:**
- `/hold`, `/unhold`
- `/approve`, `/lgtm`
- `/merge`
- `/retest`
- `/help`

## Branch Protection Rules

To fully enable auto-merge, configure branch protection for `main`:

1. Go to **Settings → Branches → Branch protection rules**
2. Add rule for `main` branch:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
     - Select: `Test on Python 3.13`, `Pre-commit checks`
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings

## Examples

### Example 1: Putting a PR on Hold

```
# Someone comments:
/hold

# Bot responds:
🚧 PR is on hold. Use `/unhold` to remove the hold.

# Label 'do-not-merge/hold' is added
```

### Example 2: Approving and Merging

```
# Review the code, then comment:
/lgtm

# Bot approves and adds 'lgtm' label

# Once all checks pass, comment:
/merge

# Bot merges the PR
```

### Example 3: Dependabot Auto-Merge

```
# Dependabot opens PR for pytest 8.4.2 → 8.5.0 (minor update)
# CI runs and passes
# Bot auto-approves
# Bot enables auto-merge
# PR merges automatically
```

### Example 4: Major Update Requires Manual Review

```
# Dependabot opens PR for black 24.0.0 → 25.0.0 (major update)
# CI runs and passes
# Bot comments: "⚠️ Major version update detected - requires manual review"
# Requires manual `/approve` and `/merge`
```

## Troubleshooting

### Auto-merge not working?

Check:
1. Branch protection rules are configured
2. All required status checks are passing
3. No `do-not-merge/hold` label is present
4. PR is from Dependabot (for auto-merge workflow)

### Commands not responding?

Check:
1. Command is typed exactly as shown (case-sensitive)
2. Command is the only text in the comment
3. You have write access to the repository
4. Workflows have necessary permissions

### Need to bypass auto-merge?

Use `/hold` before CI completes, or close the PR and reopen after making changes.

## Security Considerations

- Only users with write access can use PR commands
- Major version updates are never auto-merged
- Auto-merge requires passing CI checks
- Branch protection prevents force pushes

## Related Documentation

- [Dependabot Configuration](./DEPENDABOT.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [CI Workflow](../workflows/ci.yml)
