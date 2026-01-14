# Branch Naming Convention

This repository enforces Git best practices for branch naming.

## Branch Name Pattern

Branch names must follow this pattern:
```
<type>/<issue-number>-<short-description>
```

### Valid Types

- `feature/` - New features or enhancements
- `bugfix/` - Bug fixes
- `hotfix/` - Urgent production fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications
- `chore/` - Maintenance tasks, dependencies, tooling

### Examples

✅ **Valid:**
- `feature/123-add-aws-sigv4`
- `bugfix/456-fix-credential-leak`
- `hotfix/789-patch-security-vuln`
- `docs/update-readme`
- `refactor/cleanup-strategies`
- `test/add-integration-tests`
- `chore/update-dependencies`

❌ **Invalid:**
- `my-branch` (no type prefix)
- `Feature/test` (wrong case)
- `feature_test` (underscore instead of slash)
- `fix` (too generic)
- `feature/add something` (spaces not allowed)

### Rules

1. **Type prefix required** - Must start with valid type followed by `/`
2. **Lowercase only** - All characters must be lowercase
3. **Hyphens for separation** - Use `-` between words, not spaces or underscores
4. **Issue reference recommended** - Include issue number when applicable
5. **Descriptive** - Use clear, concise descriptions
6. **No special characters** - Only alphanumeric, hyphens, and slashes

### Enforcement

Branch protection rules enforce this pattern via:
```regex
^(feature|bugfix|hotfix|docs|refactor|test|chore)\/[a-z0-9-]+$
```

### Protected Branches

- `main` - Production-ready code (requires PR reviews)
- `develop` - Integration branch (if used)

### Creating a Branch

```bash
# Feature branch
git checkout -b feature/123-new-feature

# Bug fix
git checkout -b bugfix/456-fix-issue

# Documentation
git checkout -b docs/update-guide
```

### References

- [Git Branch Naming Best Practices](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
- [Conventional Commits](https://www.conventionalcommits.org/)
