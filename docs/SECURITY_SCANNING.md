# Security Scanning Documentation

This document describes the automated security scanning implemented for CloakCode.

---

## Overview

CloakCode implements comprehensive automated security scanning through GitHub Actions. Every push to main triggers multiple security tools to detect vulnerabilities, misconfigurations, and security issues.

---

## Scanning Tools

### 1. **Trivy** - Container & Filesystem Scanner

**What it scans:**
- Docker container images (proxy and agent)
- Filesystem for vulnerabilities
- OS packages
- Application dependencies

**Severity levels:** CRITICAL, HIGH, MEDIUM

**Output:** Results appear in GitHub Security → Code Scanning

### 2. **Safety** - Python Dependency CVE Scanner

**What it scans:**
- Python packages in `proxy/requirements.txt`
- Development dependencies in `requirements-dev.txt`

**Database:** Known CVE database for Python packages

### 3. **pip-audit** - Python CVE Scanner

**What it scans:**
- Python dependencies for known CVEs
- Uses the OSV (Open Source Vulnerabilities) database

**Output:** JSON reports with CVE details

### 4. **Bandit** - Python Code Security

**What it scans:**
- Python source code for security issues
- Common security anti-patterns
- Hardcoded credentials, SQL injection risks, etc.

**Files scanned:** `proxy/`, `tests/`

### 5. **Hadolint** - Dockerfile Security

**What it scans:**
- Dockerfile best practices
- Security misconfigurations
- Unnecessary privileges
- Image layer optimization

**Files scanned:** `proxy/Dockerfile`, `agent/Dockerfile`

### 6. **Gitleaks** - Secrets Detection

**What it scans:**
- Git history for exposed secrets
- API keys, passwords, tokens
- Private keys

**Scope:** Entire git history

### 7. **CodeQL** - Code Security Analysis

**What it scans:**
- Python code for security vulnerabilities
- Code quality issues
- Security-related code patterns

**Queries:** Security and quality queries

### 8. **Dependency Review**

**What it scans:**
- New dependencies in PRs
- Known vulnerabilities in dependencies
- License compliance

**Trigger:** Pull requests only

### 9. **SBOM Generation**

**What it creates:**
- Software Bill of Materials (SBOM)
- Complete inventory of components
- SPDX format for compliance

---

## Scan Triggers

### Automatic Triggers

1. **Push to main or develop**
   - Full security scan runs
   - Results uploaded to Security tab

2. **Pull Requests to main**
   - All scans run
   - Dependency review checks new dependencies
   - Results commented on PR

3. **Daily Schedule**
   - Runs at 2 AM UTC daily
   - Catches newly discovered vulnerabilities

4. **Manual Trigger**
   - Can be triggered via GitHub Actions UI
   - Useful for testing or on-demand scans

---

## Viewing Results

### GitHub Security Tab

1. Navigate to repository → **Security** tab
2. Click **Code scanning**
3. View all detected issues by severity
4. Filter by tool, severity, or status

### GitHub Actions

1. Navigate to **Actions** tab
2. Click on **Security Vulnerability Scan** workflow
3. View detailed logs for each scan job

### Pull Request Comments

For PRs, a summary comment is automatically posted with:
- Scan status for each tool
- Link to detailed results
- Quick overview of findings

---

## Interpreting Results

### Severity Levels

| Severity | Action Required | Timeline |
|----------|----------------|----------|
| **CRITICAL** | Fix immediately | Within 24 hours |
| **HIGH** | Fix soon | Within 1 week |
| **MEDIUM** | Plan to fix | Within 1 month |
| **LOW** | Consider fixing | As time allows |

### Common Issues

#### Container Vulnerabilities
- **Issue:** OS package with known CVE
- **Fix:** Update base image or package version
- **Example:** `apt-get update && apt-get upgrade`

#### Python Dependencies
- **Issue:** Package with security vulnerability
- **Fix:** Update package in requirements.txt
- **Example:** `mitmproxy>=10.2.0` (specify minimum safe version)

#### Dockerfile Issues
- **Issue:** Running as root user
- **Fix:** Use USER directive in Dockerfile
- **Example:** Already implemented in our Dockerfiles

#### Secrets Detected
- **Issue:** API key in git history
- **Fix:** 
  1. Revoke the exposed secret immediately
  2. Use git-filter-repo to remove from history
  3. Generate new credentials

---

## False Positives

### Marking False Positives

1. Go to Security → Code scanning
2. Click on the alert
3. Click **Dismiss alert**
4. Select reason (e.g., "Used in tests", "Risk is tolerable")
5. Add comment explaining why

### Common False Positives

- **Bandit B108 (hardcoded temp file):** Often acceptable in test code
- **Trivy in base images:** Sometimes unavoidable, assess actual risk
- **Hadolint DL3008:** pinning apt packages can make builds fragile

---

## Fixing Vulnerabilities

### Python Dependencies

```bash
# Update specific package
pip install --upgrade package-name

# Check for updates
pip list --outdated

# Update requirements file
pip freeze > requirements.txt
```

### Container Images

```dockerfile
# Update base image
FROM python:3.11-slim-bookworm  # Use latest patch version

# Update packages during build
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### Code Issues

```python
# Before (Bandit will flag this)
password = "hardcoded_password"

# After (Read from environment)
import os
password = os.environ.get("PASSWORD")
```

---

## Suppressing Warnings

### Bandit

```python
# Suppress specific check
import subprocess
subprocess.run(shell=True)  # nosec B602 - controlled input

# Suppress for entire file
# bandit: skip_file
```

### Trivy

Create `.trivyignore`:
```
# Ignore specific CVE with reason
CVE-2024-12345  # Fixed in next base image update
```

### Hadolint

```dockerfile
# Ignore specific rule
# hadolint ignore=DL3008
RUN apt-get install -y python3
```

---

## CI/CD Integration

### Fail Build on Critical Issues

To make builds fail on critical vulnerabilities, modify the workflow:

```yaml
- name: Run Trivy vulnerability scanner on Proxy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'cloakcode-proxy:test'
    format: 'sarif'
    output: 'trivy-proxy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'  # Changed from '0' to fail on findings
```

### Branch Protection

Recommended branch protection rules:
1. Require status checks to pass before merging
2. Require security scans to complete
3. Require approval from code owners
4. Prevent force pushes

---

## Compliance & Reporting

### SBOM (Software Bill of Materials)

Generated automatically on each scan:
- Location: Actions → Artifacts → `sbom-files`
- Format: SPDX JSON
- Use for: Compliance, auditing, license tracking

### Audit Trail

All scan results are:
- Stored in GitHub Security tab
- Timestamped and tracked
- Accessible via GitHub API
- Exportable for compliance reports

---

## Best Practices

### For Developers

1. **Run scans locally** before pushing:
   ```bash
   # Scan with Trivy
   docker build -t test-image .
   trivy image test-image
   
   # Check Python dependencies
   pip-audit -r requirements.txt
   
   # Scan code with Bandit
   bandit -r .
   ```

2. **Keep dependencies updated**:
   ```bash
   pip list --outdated
   pip install --upgrade package-name
   ```

3. **Review security alerts** promptly:
   - Check Security tab weekly
   - Address CRITICAL/HIGH issues immediately
   - Plan fixes for MEDIUM issues

4. **Never commit secrets**:
   - Use `.gitignore` for sensitive files
   - Use environment variables
   - Use git pre-commit hooks

### For Maintainers

1. **Monitor daily scans** for new vulnerabilities
2. **Triage alerts** by severity and exploitability
3. **Document decisions** when dismissing alerts
4. **Update base images** regularly
5. **Review SBOM** for license compliance

---

## Emergency Response

### Critical Vulnerability Found

1. **Assess impact**:
   - Is the vulnerable component actually used?
   - Is it exposed to untrusted input?
   - Is there an exploit available?

2. **Immediate actions**:
   - Create hotfix branch
   - Apply fix or workaround
   - Test thoroughly
   - Deploy to production

3. **Communication**:
   - Notify team via Slack/email
   - Update security advisory
   - Document incident

---

## Resources

- **Trivy Documentation**: https://trivy.dev/
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CVE Database**: https://cve.mitre.org/
- **GitHub Security**: https://docs.github.com/en/code-security

---

## Questions?

For questions about security scanning:
- Check GitHub Actions logs for detailed errors
- Review this documentation
- Contact security team
- Create an issue in the repository

---

**Last Updated:** 2026-01-13  
**Maintained By:** Security Team
