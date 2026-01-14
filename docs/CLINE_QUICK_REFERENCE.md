# Cline Quick Reference for CloakCode

**One-page cheat sheet for using Cline with CloakCode**

---

## 🚀 Quick Setup (5 Minutes)

```bash
# 1. Run the setup script
./scripts/setup-cline.sh

# 2. Connect VS Code to container
# In VS Code: Cmd/Ctrl+Shift+P → "Remote-Containers: Attach to Running Container..."
# Select: cloakcode_agent

# 3. Configure Cline
# Click Cline icon → Settings
# API Provider: Anthropic
# API Key: DUMMY_ANTHROPIC_KEY
```

---

## 🔑 Dummy Credentials Reference

Use these EXACT values in Cline configuration:

| Provider | Dummy Credential |
|----------|------------------|
| **Anthropic** | `DUMMY_ANTHROPIC_KEY` |
| **OpenAI** | `DUMMY_OPENAI_KEY` |
| **IBM ICA** | `DUMMY_ICA_KEY` |
| **AWS** | `AKIA00000000DUMMYKEY` |
| **GitHub** | `DUMMY_GITHUB_TOKEN` |

---

## 📝 Common Cline Commands

### File Operations
```
"Read all Python files and add docstrings"
"Create a new module called auth.py"
"Refactor this function to be more efficient"
"Find all TODO comments in the project"
```

### Code Generation
```
"Create a REST API endpoint for user authentication"
"Write unit tests for the UserService class"
"Generate a Dockerfile for this Python app"
"Create a bash script to backup the database"
```

### Debugging
```
"Help me debug this error: [paste error]"
"Why is this function returning None?"
"Review this code for security issues"
"Optimize this database query"
```

### Git Operations
```
"Create a new branch called feature/auth"
"Commit these changes with a descriptive message"
"Show me what files have changed"
"Create a PR description for these changes"
```

---

## 🔍 Monitoring & Verification

### Check Credential Injection
```bash
# On host machine
tail -f logs/proxy_injections.log

# Look for:
# [2026-01-13 07:30:45] INJECTION: api.anthropic.com
#   Trigger: DUMMY_ANTHROPIC_KEY detected
#   Strategy: anthropic-cline
#   Status: SUCCESS
```

### Container Status
```bash
# Check containers are running
docker-compose ps

# View proxy logs
docker logs cloakcode_proxy

# View agent logs
docker logs cloakcode_agent
```

### Test Proxy Connection
```bash
# Inside container (VS Code terminal)
curl -v http://proxy:8080

# Should return 200 OK
```

---

## 🛠️ Troubleshooting

### Cline Not Working

**Problem:** Cline shows API errors

**Fix:**
```bash
# 1. Verify dummy credential in Cline settings
#    Must be EXACTLY: DUMMY_ANTHROPIC_KEY

# 2. Check proxy is running
docker-compose ps

# 3. Restart proxy
docker-compose restart proxy

# 4. Check logs
tail -f logs/proxy_injections.log
```

### Extensions Not Installing

**Problem:** Cline missing after connecting

**Fix:**
```bash
# 1. Check devcontainer.json exists
cat .devcontainer/devcontainer.json

# 2. Reconnect VS Code to container
# Cmd/Ctrl+Shift+P → "Remote-Containers: Reopen in Container"

# 3. Manual install
# In remote session: Extensions → Search "Cline" → Install
```

### Container Connection Failed

**Problem:** VS Code can't connect to container

**Fix:**
```bash
# 1. Rebuild containers
docker-compose down
docker-compose up -d --build

# 2. Verify container is running
docker ps | grep cloakcode_agent

# 3. Check container logs
docker logs cloakcode_agent
```

---

## 🔒 Security Best Practices

✅ **DO:**
- Use DUMMY credentials in Cline
- Monitor `logs/proxy_injections.log` regularly
- Review `logs/audit.json` for security events
- Reset container if compromised: `docker-compose down && docker-compose up -d`

❌ **DON'T:**
- Never use real API keys in Cline configuration
- Never hardcode credentials in your code
- Never commit `.env` file to git
- Never share credentials in chat/prompts

---

## 📂 Important Files

| File | Purpose |
|------|---------|
| `.devcontainer/devcontainer.json` | VS Code container configuration |
| `.clinerules` | Cline behavior guidelines |
| `proxy/config.yaml` | Credential injection rules |
| `.env` | Real credentials (git-ignored) |
| `logs/proxy_injections.log` | Injection event log |
| `logs/audit.json` | Structured audit trail |

---

## 🔄 Common Workflows

### Rebuild After Config Changes
```bash
docker-compose down
docker-compose up -d --build
docker-compose logs -f
```

### View All Logs
```bash
# Real-time monitoring
tail -f logs/*.log

# Search for errors
grep -i error logs/*.log

# Count injections
grep "Status: SUCCESS" logs/proxy_injections.log | wc -l
```

### Connect to Container Terminal
```bash
# From host
docker exec -it cloakcode_agent bash

# Inside container
cd workspace
ls -la
```

---

## 🆘 Emergency Procedures

### Container Compromised
```bash
# 1. Stop containers immediately
docker-compose down

# 2. Check logs for suspicious activity
grep -i "BLOCKED\|ERROR" logs/*.log

# 3. Review audit trail
cat logs/audit.json | jq '.[] | select(.status=="BLOCKED")'

# 4. Rotate credentials
# Update .env with new API keys
# Update proxy/config.yaml if needed

# 5. Rebuild clean
docker-compose up -d --build
```

### Credential Leak Suspected
```bash
# 1. Immediately revoke exposed credentials at provider
# 2. Check git history
git log --all -- .env
git log -S "YOUR_API_KEY" --all

# 3. Verify .env is in .gitignore
cat .gitignore | grep .env

# 4. Generate new credentials
# 5. Update .env file
# 6. Restart proxy
docker-compose restart proxy
```

---

## 📚 More Information

- **Full Setup Guide:** `docs/CLINE_SETUP.md`
- **Main README:** `README.md`
- **Logging Docs:** `docs/LOGGING.md`
- **CloakCode Docs:** `docs/Universal Injector Architecture.md`

---

## 💡 Pro Tips

1. **Use Memory Bank** for complex projects - create `workspace/memory-bank/` directory
2. **Set up aliases** for common commands in `~/.bashrc`
3. **Monitor proxy health** with `docker logs cloakcode_proxy --tail 50`
4. **Use Plan Mode** in Cline for complex tasks before execution
5. **Create .clinerules** templates for different project types

---

**Questions? Check the full documentation or run: `./scripts/setup-cline.sh`**
