# Persistent Logging Guide

## Overview

CloakCode v2.0 includes comprehensive persistent logging that tracks all important events across container destruction and recreation. Logs are stored on the host filesystem and survive `docker-compose down`.

## Log Files

All logs are stored in the `./logs/` directory on the host:

```
logs/
├── agent_activity.log      # Agent container activity (npm, git, pip, etc.)
├── proxy_injections.log    # Credential injection events
├── security_events.log     # Security-related events (blocks, violations)
├── audit.json             # Structured JSON audit trail
└── .bash_history          # Persistent bash command history
```

---

## Agent Activity Logs

**Location:** `logs/agent_activity.log`

**Contains:**
- Package installations (npm, pip, pip3)
- Git operations (clone, push, pull, commit)
- Sudo command execution
- Container start/stop events
- Command execution with timestamps
- Error messages from failed operations

**Example:**
```
[2026-01-13T06:42:15+00:00] Container Started
[2026-01-13T06:42:15+00:00] User: agent
[2026-01-13T06:42:15+00:00] Hostname: agent
[2026-01-13T06:42:30+00:00] NPM: install -g @anthropic-ai/claude-code
[2026-01-13T06:43:05+00:00] GIT: clone git@github.com:user/repo.git
[2026-01-13T06:43:15+00:00] PIP: install requests
[2026-01-13T06:44:00+00:00] SUDO: apt-get install jq
```

**View in real-time:**
```bash
# From host
tail -f logs/agent_activity.log

# From inside container
tail -f ~/logs/agent_activity.log
```

---

## Proxy Injection Logs

**Location:** `logs/proxy_injections.log`

**Contains:**
- Credential injection events
- Strategy name used
- Target hostname
- Success/failure status
- Error details (if failed)

**Example:**
```
[2026-01-13T06:45:00Z] credential_injection: api.github.com | Strategy: github | Status: SUCCESS
[2026-01-13T06:45:10Z] credential_injection: api.openai.com | Strategy: openai | Status: SUCCESS
[2026-01-13T06:45:20Z] credential_injection: s3.amazonaws.com | Strategy: aws-prod | Status: SUCCESS
[2026-01-13T06:45:30Z] credential_injection: api.stripe.com | Strategy: stripe-live | Status: FAILED | Invalid token format
```

**View:**
```bash
tail -f logs/proxy_injections.log
```

**Count injections:**
```bash
grep "Status: SUCCESS" logs/proxy_injections.log | wc -l
```

---

## Security Event Logs

**Location:** `logs/security_events.log`

**Contains:**
- Telemetry blocking events
- Failed injection attempts
- Security violations
- Unauthorized access attempts

**Example:**
```
[2026-01-13T06:46:00Z] telemetry_blocked: telemetry.anthropic.com | Action: BLOCKED | Reason: Telemetry/analytics endpoint
[2026-01-13T06:46:10Z] injection_failure: api.example.com | Action: BLOCKED | Reason: Fail-closed mode: Invalid credential
[2026-01-13T06:46:20Z] telemetry_blocked: sentry.io | Action: BLOCKED | Reason: Telemetry/analytics endpoint
```

**View:**
```bash
tail -f logs/security_events.log
```

**Count blocked requests:**
```bash
grep "Action: BLOCKED" logs/security_events.log | wc -l
```

---

## Structured Audit Log

**Location:** `logs/audit.json`

**Contains:**
- All events in JSON format
- Machine-parseable
- Suitable for log aggregation systems
- Includes all metadata

**Example:**
```json
{"timestamp":"2026-01-13T06:45:00Z","event_type":"credential_injection","host":"api.github.com","strategy":"github","status":"SUCCESS","details":""}
{"timestamp":"2026-01-13T06:45:10Z","event_type":"command_execution","data":{"message":"NPM install -g @anthropic-ai/claude-code"}}
{"timestamp":"2026-01-13T06:45:20Z","event_type":"git_clone","data":{"message":"Repository: git@github.com:user/repo.git"}}
{"timestamp":"2026-01-13T06:46:00Z","event_type":"telemetry_blocked","host":"telemetry.anthropic.com","action":"BLOCKED","reason":"Telemetry/analytics endpoint"}
```

**View with jq:**
```bash
# Pretty print
cat logs/audit.json | jq

# Filter by event type
cat logs/audit.json | jq 'select(.event_type == "credential_injection")'

# Count events by type
cat logs/audit.json | jq -s 'group_by(.event_type) | map({type: .[0].event_type, count: length})'

# Filter by timestamp
cat logs/audit.json | jq 'select(.timestamp > "2026-01-13T06:00:00Z")'

# Extract successful injections
cat logs/audit.json | jq 'select(.event_type == "credential_injection" and .status == "SUCCESS")'
```

---

## Bash Command History

**Location:** `logs/.bash_history`

**Contains:**
- All bash commands executed in the agent container
- Timestamped entries
- Persistent across container restarts

**View:**
```bash
# From host
cat logs/.bash_history

# From inside container
history

# Search history
history | grep "npm install"
```

---

## Log Rotation

Logs are automatically rotated when they exceed 50MB:

- Original log file is renamed with timestamp: `agent_activity.log.20260113_064500`
- Rotated file is compressed: `agent_activity.log.20260113_064500.gz`
- New log file is created automatically
- Old logs are kept (not automatically deleted)

**Manual cleanup:**
```bash
# Remove logs older than 30 days
find logs/ -name "*.gz" -mtime +30 -delete

# Remove all compressed logs
rm logs/*.gz
```

---

## Accessing Logs

### From Host Machine

```bash
# View all logs
ls -lh logs/

# Tail all logs simultaneously
tail -f logs/*.log

# Search across all logs
grep "error" logs/*.log

# View specific log
less logs/agent_activity.log
```

### From Agent Container

```bash
# Enter container
docker-compose exec agent bash

# View logs
tail -f ~/logs/agent_activity.log

# Search logs
grep "npm install" ~/logs/agent_activity.log

# View audit trail
cat ~/logs/audit.json | jq
```

### From Proxy Container

Proxy logs are written to the same `/logs` volume:

```bash
# View proxy injections
docker-compose exec proxy cat /logs/proxy_injections.log

# View security events
docker-compose exec proxy cat /logs/security_events.log
```

---

## What Gets Logged

### Automatically Logged Commands

The following commands are automatically logged with full output:

- **npm** / **npm install** / **npm run**
- **pip** / **pip3** / **pip install**
- **git** (all git commands)
- **sudo** (security-sensitive operations)

### Automatically Logged Events

- **Container lifecycle:** Start, stop, restart
- **Credential injections:** Every API request with credential replacement
- **Security events:** Telemetry blocks, injection failures
- **Git operations:** Clone, push, pull with repository details
- **Package installations:** Package name, version, success/failure
- **SSH operations:** Key setup, cleanup

---

## Log Analysis Examples

### Find all npm installations
```bash
grep "NPM: install" logs/agent_activity.log
```

### Count successful credential injections by service
```bash
cat logs/audit.json | jq -r 'select(.event_type == "credential_injection" and .status == "SUCCESS") | .host' | sort | uniq -c
```

### Find all errors
```bash
grep -i "error" logs/*.log
```

### Track git operations
```bash
grep "GIT:" logs/agent_activity.log
```

### Security audit - find all blocks
```bash
cat logs/audit.json | jq 'select(.action == "BLOCKED")'
```

### Most used commands
```bash
cat logs/.bash_history | cut -d' ' -f1 | sort | uniq -c | sort -rn | head -10
```

---

## Monitoring & Alerts

### Real-time Monitoring

```bash
# Watch for injection failures
tail -f logs/proxy_injections.log | grep "FAILED"

# Watch for security blocks
tail -f logs/security_events.log | grep "BLOCKED"

# Watch for errors
tail -f logs/agent_activity.log | grep -i "error"
```

### Daily Summary Script

```bash
#!/bin/bash
# daily_summary.sh

echo "=== CloakCode Daily Log Summary ==="
echo ""
echo "Credential Injections:"
grep "credential_injection" logs/audit.json | jq -s 'group_by(.status) | map({status: .[0].status, count: length})'
echo ""
echo "Security Blocks:"
grep "telemetry_blocked" logs/audit.json | wc -l
echo ""
echo "Top Commands:"
grep "NPM:\|GIT:\|PIP:" logs/agent_activity.log | cut -d: -f2 | cut -d' ' -f2 | sort | uniq -c | sort -rn | head -5
```

---

## Backup & Export

### Backup Logs

```bash
# Create timestamped backup
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Backup to remote server
rsync -avz logs/ user@backup-server:/backups/cloakcode-logs/
```

### Export for Analysis

```bash
# Export to JSON
cat logs/audit.json > audit-export-$(date +%Y%m%d).json

# Export to CSV (requires jq)
cat logs/audit.json | jq -r '[.timestamp, .event_type, .host, .status] | @csv' > audit.csv
```

---

## Integration with Log Management Systems

### Shipping to Elasticsearch

```bash
# Using Filebeat
filebeat.inputs:
- type: log
  paths:
    - /path/to/logs/audit.json
  json.keys_under_root: true
```

### Shipping to Splunk

```bash
# Using Splunk Universal Forwarder
[monitor:///path/to/logs/]
sourcetype = cloakcode
index = security
```

### Shipping to CloudWatch

```python
# Using AWS CloudWatch Logs
import boto3
import json

logs = boto3.client('logs')

with open('logs/audit.json') as f:
    for line in f:
        event = json.loads(line)
        logs.put_log_events(
            logGroupName='/cloakcode/audit',
            logStreamName='agent',
            logEvents=[{
                'timestamp': int(datetime.fromisoformat(event['timestamp']).timestamp() * 1000),
                'message': json.dumps(event)
            }]
        )
```

---

## Troubleshooting

### Logs not appearing

```bash
# Check log directory exists
ls -ld logs/

# Check permissions
ls -l logs/

# Check volume mount
docker-compose exec agent ls -l /home/agent/logs/

# Check logging utilities are loaded
docker-compose exec agent type log_event
```

### Log files too large

```bash
# Check file sizes
du -h logs/*

# Manually rotate
mv logs/agent_activity.log logs/agent_activity.log.$(date +%Y%m%d)
gzip logs/agent_activity.log.$(date +%Y%m%d)

# Restart containers to create new log files
docker-compose restart
```

### Missing log entries

```bash
# Check if logging functions are active
docker-compose exec agent bash -c 'type log_event'

# Verify aliases are set
docker-compose exec agent bash -c 'alias'

# Check log file permissions
docker-compose exec agent ls -l ~/logs/
```

---

## Best Practices

1. **Regular Review:** Review logs daily for anomalies
2. **Backup:** Backup logs weekly to remote storage
3. **Rotation:** Clean up old compressed logs monthly
4. **Monitoring:** Set up alerts for injection failures and security blocks
5. **Analysis:** Use the structured JSON log for automated analysis
6. **Security:** Restrict access to log files (they may contain sensitive metadata)
7. **Retention:** Define a log retention policy (e.g., 90 days)

---

## Privacy & Security

**Note:** While logs don't contain actual credentials, they do contain:
- Hostnames of API services accessed
- Timestamps of operations
- Command execution history
- Package installation history

Treat logs as **sensitive metadata** and:
- Restrict file permissions
- Encrypt backups
- Limit access to authorized personnel only
- Comply with data retention policies

---

## Support

For issues with logging:
1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs`
3. Verify volume mounts in `docker-compose.yml`
4. Report issues with example log output
