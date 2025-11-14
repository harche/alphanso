# Auto-Merge Security Model

This document explains the security controls for auto-merge and PR commands.

## Security Principles

1. **Dependabot PRs are auto-merged automatically** - Minor/patch updates only
2. **External contributor PRs require dual approval** - Both `/approve` AND `/lgtm` from owner
3. **PR commands require write access** - Only maintainers/collaborators can use them
4. **Branch protection is required** - Prevents bypassing checks
5. **Major updates need manual review** - Breaking changes never auto-merge
6. **Multiple approval layers** - CI + manual approval + branch protection

## Auto-Merge Security Controls

### 1. Multi-Layer Actor Verification

```yaml
if: |
  github.event.pull_request.user.login == 'dependabot[bot]' &&
  github.event.pull_request.author_association == 'NONE' &&
  github.event.pull_request.user.type == 'Bot'
```

**Defense in Depth - Three Independent Checks:**

**Layer 1: Username Check**
- ✅ PR author MUST be exactly `dependabot[bot]`
- ❌ Cannot register username with `[bot]` suffix - reserved by GitHub for bots only
- ❌ Fake account named "dependabot" (without suffix) won't match

**Layer 2: Author Association Check**
- ✅ Author association MUST be `NONE` (Dependabot's association type)
- ❌ GitHub controls this value - users CANNOT fake it
- ❌ Forked "dependabot" account would have `FIRST_TIME_CONTRIBUTOR` or `CONTRIBUTOR`
- ❌ Even collaborators have `COLLABORATOR`, not `NONE`

**Layer 3: User Type Check**
- ✅ User type MUST be `Bot`
- ❌ GitHub controls this value - users CANNOT fake it
- ❌ Regular user accounts have type `User`, not `Bot`
- ❌ Organization accounts have type `Organization`, not `Bot`

**Layer 4: Metadata Validation**
- ✅ Official `dependabot/fetch-metadata@v2` action validates the PR
- ❌ This action only succeeds for genuine Dependabot PRs
- ❌ Fails for any impersonation attempts

**Attack Scenarios - All Prevented:**
1. Someone creates account "dependabot" → ❌ Missing `[bot]` suffix (Layer 1 fails)
2. Someone uses git config to fake author → ❌ GitHub sets author from account (Layer 2/3 fail)
3. Someone compromises a fork → ❌ Wrong author_association (Layer 2 fails)
4. Malicious bot account tries to impersonate → ❌ Wrong username and association (Layers 1+2 fail)

### 2. Version Update Type Check

```yaml
if: steps.metadata.outputs.update-type != 'version-update:semver-major'
```

**Checks:**
- ✅ Patch updates (1.2.3 → 1.2.4) - Auto-merge
- ✅ Minor updates (1.2.x → 1.3.0) - Auto-merge
- ❌ Major updates (1.x.x → 2.0.0) - Manual review required

### 3. CI Must Pass

**Requirements:**
- All status checks defined in branch protection must pass
- Auto-merge only triggers AFTER checks complete successfully
- Failed checks = no merge

### 4. Branch Protection (Required)

**Must configure in Settings → Branches:**

```
✅ Require pull request before merging
✅ Require approvals: 1 (can be auto-approval for Dependabot)
✅ Require status checks to pass:
   - Test on Python 3.13
   - Pre-commit checks
✅ Require conversation resolution
✅ Do not allow bypassing settings
❌ Allow force pushes: disabled
❌ Allow deletions: disabled
```

**Without branch protection:**
- Auto-merge workflows can approve but won't merge
- Manual merge still requires passing checks

## External Contributor Auto-Merge Security Controls

### 1. Dual Approval Requirement

```yaml
# External PR Auto-Merge Workflow
if: prAuthor !== 'harche' && prAuthor !== 'dependabot[bot]'
```

**Checks:**
- ✅ PR must have approval review from repository owner (@harche)
- ✅ PR must have `lgtm` label (added via `/lgtm` command by @harche)
- ❌ Single approval is not sufficient - both are required
- ❌ PRs from owner or dependabot are excluded from this workflow

### 2. Owner-Only Approval

```javascript
const harcheApproval = reviews.some(review =>
  review.user.login === 'harche' && review.state === 'APPROVED'
);

const hasLgtmLabel = pr.labels.some(label => label.name === 'lgtm');
```

**Requirements:**
- ✅ Only approvals from @harche count
- ✅ Only lgtm labels added by @harche (via `/lgtm` command) count
- ❌ Approvals from other maintainers do not trigger auto-merge
- ❌ Manual label additions without `/lgtm` command are not reliable

### 3. Workflow Triggers

**Triggers on:**
- `pull_request_review.submitted` - When someone submits a review
- `issue_comment.created` - When someone comments (for `/lgtm` command)

**Why both triggers:**
- `/approve` creates a review → triggers `pull_request_review` event
- `/lgtm` adds label + creates review → triggers both events
- Workflow checks conditions on every trigger to enable auto-merge

### 4. CI Must Still Pass

**Requirements:**
- Auto-merge is enabled, but merge only happens when CI passes
- If CI fails, PR remains in "auto-merge pending" state
- Owner can use `/hold` to cancel auto-merge at any time

## PR Commands Security Controls

### 1. Author Association Check

```javascript
const allowedAssociations = ['OWNER', 'MEMBER', 'COLLABORATOR'];
if (!allowedAssociations.includes(commenterAssociation)) {
  return; // Silently ignore
}
```

**Who can use commands:**
- ✅ **OWNER** - Repository owner
- ✅ **MEMBER** - Organization members
- ✅ **COLLABORATOR** - Added collaborators with write access
- ❌ **CONTRIBUTOR** - Has contributed but no write access
- ❌ **FIRST_TIME_CONTRIBUTOR** - First-time contributor
- ❌ **NONE** - External user

### 2. Command-Specific Permissions

| Command | Requires | Additional Checks |
|---------|----------|-------------------|
| `/hold` | Write access | None |
| `/unhold` | Write access | None |
| `/approve` | Write access | Creates GitHub review |
| `/lgtm` | Write access | Creates GitHub review + label |
| `/merge` | Write access | Requires approval + passing checks |
| `/retest` | Write access | Informational only |

### 3. Merge Command Protection

```javascript
// Check if PR has required approvals
const approvals = reviews.filter(r => r.state === 'APPROVED').length;
if (approvals === 0) {
  // Error: needs approval
}
```

**Merge Requirements:**
- ✅ At least one approval review
- ✅ All CI checks passing
- ✅ Branch protection rules satisfied
- ✅ No merge conflicts

## Attack Scenarios & Mitigations

### Scenario 1: Malicious Fork with "dependabot" User

**Attack:** Create fork with user named "dependabot", create PR

**Mitigation:**
- ✅ `github.actor == 'dependabot[bot]'` specifically checks for the `[bot]` suffix
- ✅ `author_association` check ensures it's the real Dependabot
- ✅ Real Dependabot has association `NONE`, fake user would have `FIRST_TIME_CONTRIBUTOR`

**Result:** ❌ Attack fails, auto-merge doesn't trigger

### Scenario 2: External Contributor Uses PR Commands

**Attack:** External contributor comments `/merge` on their malicious PR

**Mitigation:**
- ✅ `author_association` check in PR commands workflow
- ✅ Only `OWNER`, `MEMBER`, `COLLABORATOR` can use commands
- ✅ External contributors silently ignored (no error message to avoid spam)

**Result:** ❌ Attack fails, command ignored

### Scenario 3: Compromised Dependency with Malicious Update

**Attack:** Legitimate Dependabot PR updates to compromised package version

**Mitigation:**
- ✅ Branch protection requires CI to pass
- ✅ Tests run in CI can catch malicious behavior (if tests cover it)
- ⚠️ Major updates require manual review (breaking changes often investigated)
- ⚠️ Supply chain attacks still possible if tests don't detect malicious code

**Recommendation:**
- Enable Dependabot security updates
- Review changelogs, especially for major updates
- Use tools like Snyk or Dependabot security advisories
- Consider requiring 2 approvals for dependency updates

### Scenario 4: PR from Forked Repository

**Attack:** Create fork, modify workflows, create PR with malicious changes

**Mitigation:**
- ✅ GitHub Actions workflows from forks don't have write permissions by default
- ✅ `pull_request_target` used instead of `pull_request` for auto-merge
- ✅ Workflows check `github.actor` and `author_association`
- ✅ Branch protection prevents direct merges

**Result:** ❌ Attack fails, no write permissions granted to fork workflows

### Scenario 5: Workflow Injection via PR Title/Description

**Attack:** Inject malicious code via PR title or description that gets executed in workflow

**Mitigation:**
- ✅ We don't use PR title/description in workflow commands
- ✅ All workflow inputs are from GitHub context (trusted)
- ✅ No `eval` or shell expansion of PR content

**Result:** ❌ Attack fails, no injection points

## Best Practices

### 1. Enable Branch Protection

**Critical for security:**

```bash
# Via GitHub UI or API
# Settings → Branches → Add rule for 'main'
```

Without branch protection:
- Anyone with write access can force push
- Status checks can be bypassed
- Auto-merge has reduced security

### 2. Review Dependabot PRs Regularly

**Weekly review:**
- Check for major updates (not auto-merged)
- Review changelogs of dependency updates
- Monitor for suspicious changes

### 3. Limit Repository Write Access

**Principle of least privilege:**
- Only give `COLLABORATOR` to trusted users
- Use teams for organization repositories
- Review access regularly

### 4. Monitor Workflow Runs

**Watch for:**
- Failed workflows (could indicate attacks)
- Unexpected auto-merges
- Commands from unexpected users (should be ignored, but monitor)

### 5. Enable GitHub Security Features

**Recommended:**
- ✅ Dependabot security updates
- ✅ Dependabot version updates
- ✅ Code scanning (CodeQL)
- ✅ Secret scanning
- ✅ Dependency review

### 6. Require 2FA for Contributors

**Organization settings:**
- Require 2FA for all members
- Reduces risk of account compromise

## Audit Log

Check who triggered auto-merges:

1. Go to **Settings → Security → Audit log**
2. Filter by: `action:pull_request.auto_merge_enabled`
3. Verify `actor` is `dependabot[bot]`

## Incident Response

If you suspect abuse:

1. **Immediately disable auto-merge:**
   ```bash
   # Rename workflow file to disable
   git mv .github/workflows/dependabot-auto-merge.yml \
          .github/workflows/dependabot-auto-merge.yml.disabled
   ```

2. **Review recent merges:**
   ```bash
   git log --merges --since="1 week ago" --oneline
   ```

3. **Check for malicious changes:**
   ```bash
   git diff HEAD~10..HEAD
   ```

4. **Re-enable after investigation**

## Testing Security Controls

### Test 1: External Contributor Command

```bash
# As external contributor, comment on PR:
/merge

# Expected: Command silently ignored
# Actual: Check workflow run logs
```

### Test 2: Non-Dependabot PR Auto-Merge

```bash
# Create PR from your own account
# Expected: Auto-merge workflow doesn't run
# Verify: Check Actions tab
```

### Test 3: Major Update

```bash
# Wait for Dependabot major update PR
# Expected: PR created but not auto-merged
# Expected: Comment about manual review
```

## Questions?

- **Q: Can I disable auto-merge for specific dependencies?**
  - A: Yes, use Dependabot's ignore feature: `@dependabot ignore this dependency`

- **Q: Can I require manual approval even for minor updates?**
  - A: Yes, modify workflow to remove auto-approve job or add conditions

- **Q: What if branch protection isn't configured?**
  - A: Auto-merge will approve but won't merge until protection is added

- **Q: Can organization members from any team use commands?**
  - A: Only if they have write access to the repository

## Related Documentation

- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Dependabot Security Updates](https://docs.github.com/en/code-security/dependabot/dependabot-security-updates)
- [GitHub Actions Security](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
