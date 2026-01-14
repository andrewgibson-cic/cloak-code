# Project Evolution History

## CloakCode: From Go Prototype to Enterprise Python Implementation

This document chronicles the evolution of CloakCode from its origins as env-sidecar through to its current enterprise implementation.

---

## Timeline

### Phase 1: env-sidecar (Go Implementation)
**Repository:** https://github.com/harryslimes/env-sidecar  
**Language:** Go  
**Focus:** Lightweight, standalone credential proxy

**Key Features:**
- Transparent MITM proxy using custom Go implementation
- Simple JSON configuration
- Domain-based header injection
- Variable expansion from `.env.vault`
- Magic certificate domain (mitm.it)
- Single binary deployment

**Limitations Identified:**
- No AWS Signature Version 4 support
- Limited authentication strategy options
- Basic logging capabilities
- Manual configuration for each API

---

### Phase 2: Transition Decision
**Date:** Reflected in commit `a1603d7`

After successfully deploying env-sidecar in development environments, we identified critical needs for enterprise adoption:

1. **AWS SigV4 Requirement:** Enterprise customers needed native AWS service integration
2. **Strategy Pattern:** Different APIs require different authentication schemes
3. **Enhanced Security:** Host whitelisting, credential exfiltration prevention, audit logging
4. **Complex Routing:** Priority-based rule matching for sophisticated deployments
5. **Comprehensive Monitoring:** JSON-formatted logs, rotation, persistent storage

**Decision:** Rewrite in Python using mitmproxy framework for enterprise-grade features.

---

### Phase 3: CloakCode (Python Implementation)
**Repository:** This repository  
**Language:** Python  
**Framework:** mitmproxy  
**Focus:** Enterprise credential management

**Major Enhancements:**

#### Authentication Strategies
- ✅ AWS Signature Version 4 (full implementation)
- ✅ Bearer token strategies (OpenAI, GitHub, Stripe, Gemini)
- ✅ Pluggable strategy architecture
- ✅ Custom strategy support

#### Security Features
- ✅ Zero-knowledge principle
- ✅ Per-credential host whitelisting
- ✅ Credential exfiltration prevention
- ✅ Telemetry blocking
- ✅ Fail-closed mode
- ✅ Security scanning documentation

#### Enterprise Features
- ✅ Rule-based routing with priorities
- ✅ Multiple credential sets (dev/staging/prod)
- ✅ Comprehensive audit logging (JSON format)
- ✅ Log rotation and persistence
- ✅ Kubernetes deployment manifests
- ✅ CI/CD integration examples

#### Developer Experience
- ✅ Docker Compose setup
- ✅ Automatic SSH key injection
- ✅ Persistent bash history
- ✅ Comprehensive test suite
- ✅ Detailed documentation

---

## Architecture Evolution

### env-sidecar Architecture
```
Application
    ↓ (via http_proxy environment variable)
Custom Go MITM Proxy
    ↓ (domain-based header injection)
Target API
```

**Configuration:** Simple JSON mapping of domains to headers

### CloakCode Architecture
```
Application (dummy credentials)
    ↓ (transparent iptables redirect)
mitmproxy Container
    ↓ (strategy-based authentication)
Target API (real credentials)
```

**Configuration:** YAML-based strategies, rules, and settings

---

## Git History Structure

The repository maintains the complete evolution:

```
[env-sidecar commits]
    ↓
95a7252 Initial commit: env-sidecar
4d0b08c Add replace_values feature
bae12a9 Refactor to transparent MITM proxy
d1a5866 Merge transparent proxy PR
    ↓
a1603d7 TRANSITION: Decision to rewrite in Python
    ↓
[CloakCode commits]
    ↓
3687aba Initial implementation: SafeClaude/CloakCode
2483133 Universal Injector v2 - AWS SigV4 support
69ef4d6 Rebrand to CloakCode
b75facb SSH key injection support
e409789 Latest improvements
    ↓
3f2a600 Rebrand: Rename safe-claude to cloak-code (current)
```

---

## Relationship to env-sidecar

CloakCode is **not a fork** in the GitHub sense, but represents:
- A **spiritual successor** to env-sidecar
- A **complete rewrite** with enhanced capabilities
- An **evolution** of the same core concept
- **Preservation** of the original's simplicity where possible

### What We Kept from env-sidecar
- ✅ Zero-knowledge security principle
- ✅ Transparent proxy concept
- ✅ Domain-based routing
- ✅ Environment variable expansion
- ✅ Developer-friendly setup

### What We Added
- ✅ AWS Signature Version 4
- ✅ Strategy pattern architecture
- ✅ Enterprise security features
- ✅ Comprehensive logging
- ✅ Rule-based routing
- ✅ Kubernetes support

---

## Use Case Comparison

| Use Case | env-sidecar | CloakCode |
|----------|-------------|-----------|
| **Local Development** | ✅ Excellent | ✅ Excellent |
| **AI Coding Agents** | ✅ Perfect | ✅ Good |
| **AWS Services** | ❌ Not supported | ✅ Full support |
| **Enterprise Security** | ⚠️ Basic | ✅ Comprehensive |
| **Multiple Environments** | ⚠️ Limited | ✅ Full support |
| **Kubernetes** | ⚠️ Manual | ✅ Manifests included |
| **Quick Setup** | ✅ Single binary | ⚠️ Docker required |
| **Footprint** | ✅ ~15MB | ⚠️ ~100MB |

---

## Credits

**Original Concept:** env-sidecar by harryslimes  
**Enterprise Implementation:** CloakCode team

CloakCode builds upon the innovative foundation laid by env-sidecar, extending it for enterprise use cases while maintaining the core philosophy of zero-knowledge credential management.

---

## Contributing

We welcome contributions to CloakCode! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

For the original env-sidecar project, visit: https://github.com/harryslimes/env-sidecar

---

*Last Updated: January 2026*
