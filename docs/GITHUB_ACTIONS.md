# GitHub Actions Documentation

This document describes the GitHub Actions workflows configured for the CloakCode project.

## Overview

The project uses GitHub Actions for:
- ✅ Automated releases with semantic versioning
- ✅ Continuous security scanning
- ✅ Pull request validation
- ✅ Dependency management
- ✅ Code quality checks

## Workflows

### 1. Release & Publish (`release.yml`)

**Trigger:** Push to `main` branch or manual workflow dispatch

**Purpose:** Automatically create releases with semantic versioning

#### Features
- **Semantic Versioning:** Automatically determines version bump based on commit messages
  - `feat:` commits → Minor version (2.0.0 → 2.1.0)
  - `fix:` commits → Patch version (2.0.0 → 2.0.1)
  - `feat!:` or `BREAKING CHANGE:` → Major version (2.0.0 → 3.0.0)
- **Release Notes:** Auto-generated from commits, grouped by type
- **Docker Images:** Builds and attaches to release
- **Security Scanning:** Scans images before release
- **Git Tags:** Creates annotated tags automatically
- **VERSION file:** Updates automatically

#### Manual Release

You can manually trigger a release from the Actions tab or via GitHub CLI:

```bash
gh workflow run release.yml -f version_bump=minor
```

Options:
- `auto` - Analyze commits (default)
- `major` - Force major version bump
- `minor` - Force minor version bump
- `patch` - Force patch version bump

#### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/) for automatic version detection:

```bash
# Patch version bump
git commit -m "fix: resolve credential injection bug"
git commit -m "fix(aws): correct signature v4 calculation"

# Minor version bump
git commit -m "feat: add support for Google Gemini API"
git commit -m "feat(strategies): add HMAC authentication"

# Major version bump (breaking change)
git commit -m "feat!: redesign configuration format"
git commit -m "feat: new auth system

BREAKING CHANGE: Configuration file format has changed"
```

### 2. Pull Request Validation (`pr-validation.yml`)

**Trigger:** Pull requests to `main` or `develop`

**Purpose:** Validate code quality and functionality before merging

#### Jobs

1. **Validate Commits** - Check commit message format (warning only)
2. **Lint & Format** - Check code formatting (Black, Flake8, Pylint)
3. **Unit Tests** - Run pytest with coverage reporting
4. **Docker Builds** - Verify images build correctly
5. **Security Scan** - Quick Trivy and Gitleaks scan
6. **Documentation Check** - Remind to update docs

#### Results

- Summary posted to PR as comment
- Detailed results in GitHub Actions tab
- Image sizes reported for tracking bloat

### 3. Security Vulnerability Scan (`security-scan.yml`)

**Trigger:** 
- Push to `main`/`develop`
- Pull requests
- Daily at 2 AM UTC
- Manual dispatch

**Purpose:** Comprehensive security scanning

#### Scans Performed

1. **Trivy** - Container vulnerability scanning
2. **CodeQL** - Static code analysis
3. **Python Security** - Safety, pip-audit, Bandit
4. **Hadolint** - Dockerfile best practices
5. **Gitleaks** - Secret detection
6. **SBOM Generation** - Software bill of materials
7. **Dependency Review** - Check for known vulnerabilities

### 4. Dependency Management

**Configuration:** `.github/dependabot.yml`

**Purpose:** Automated dependency updates

#### Update Schedule

- **GitHub Actions:** Weekly on Monday, 9 AM UTC
- **Python packages:** Weekly on Monday, 9 AM UTC
- **Docker images:** Weekly on Monday, 9 AM UTC

#### Automatic PRs

Dependabot will create PRs for:
- Security updates (high priority)
- Minor/patch version bumps (grouped)
- Major version bumps (individual PRs)

## Workflow Status Badges

Add these badges to your README.md:

```markdown
![Release](https://github.com/andrewgibson-cic/cloak-code/actions/workflows/release.yml/badge.svg)
![Security](https://github.com/andrewgibson-cic/cloak-code/actions/workflows/security-scan.yml/badge.svg)
![PR Validation](https://github.com/andrewgibson-cic/cloak-code/actions/workflows/pr-validation.yml/badge.svg)
```

## Best Practices

### For Contributors

1. **Use Conventional Commits** for automatic version detection
2. **Keep PRs focused** - One feature/fix per PR
3. **Update documentation** when changing functionality
4. **Wait for CI** - Don't merge failing checks
5. **Review security findings** in Security tab

### For Maintainers

1. **Review Dependabot PRs regularly**
2. **Monitor security scan results daily**
3. **Use squash merge** to maintain clean commit history
4. **Create releases from main** only
5. **Tag important releases** manually if needed

## Troubleshooting

### Release Not Created

**Problem:** Workflow runs but no release created

**Solutions:**
1. Check if there are commits since last tag
2. Verify commit messages follow conventional format
3. Check workflow logs for errors
4. Try manual dispatch with explicit version bump

### Docker Build Fails

**Problem:** Docker image build fails in CI

**Solutions:**
1. Test build locally: `docker build -t test ./proxy`
2. Check Dockerfile for syntax errors
3. Verify base image is accessible
4. Check for missing dependencies

### Security Scan False Positives

**Problem:** Security scan reports false vulnerabilities

**Solutions:**
1. Review finding in Security tab
2. Add exception if needed
3. Create issue to track
4. Update dependencies if possible

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
