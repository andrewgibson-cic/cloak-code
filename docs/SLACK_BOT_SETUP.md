# Slack Token Setup Guide

This guide walks you through creating a Slack app and obtaining tokens (Bot Token & App Token) for use with CloakCode.

---

## Overview

To use Slack API with CloakCode, you need:
1. A Slack workspace where you have admin permissions
2. A Slack app with bot capabilities
3. **Bot Token** (starts with `xoxb-`) - for API calls
4. **App Token** (starts with `xapp-`) - for Socket Mode (optional)

**Time required:** ~10-15 minutes

---

## Step-by-Step Instructions

### Step 1: Access Slack API Dashboard

1. Go to **https://api.slack.com/apps**
2. Sign in with your Slack account
3. Click **"Create New App"**

![Create New App Button](https://api.slack.com/img/api/create_new_app.png)

---

### Step 2: Choose App Creation Method

You'll see two options:

**Option A: From Scratch** (Recommended for beginners)
- Click **"From scratch"**
- Enter app name: e.g., "CloakCode Bot"
- Select workspace: Choose your workspace
- Click **"Create App"**

**Option B: From App Manifest** (Advanced)
- Use this if you have a pre-defined configuration
- Paste the manifest YAML/JSON
- Click **"Create"**

---

### Step 3: Configure Bot User

1. In the left sidebar, click **"OAuth & Permissions"**
2. Scroll down to **"Scopes"** section
3. Under **"Bot Token Scopes"**, click **"Add an OAuth Scope"**

#### Required Scopes (Minimum)

Add these scopes based on what you need:

**For Basic Messaging:**
```
chat:write          - Send messages as bot
chat:write.public   - Send messages to channels bot isn't in
```

**For Reading Messages:**
```
channels:history    - View messages in public channels
channels:read       - View basic channel info
```

**For Private Channels:**
```
groups:history      - View messages in private channels
groups:read         - View basic private channel info
```

**For Direct Messages:**
```
im:history          - View direct messages
im:read             - View basic DM info
im:write            - Send direct messages
```

**For User Information:**
```
users:read          - View people in workspace
users:read.email    - View email addresses
```

**For File Operations:**
```
files:read          - View files
files:write         - Upload files
```

**Common Recommended Scopes:**
```
app_mentions:read   - View messages that mention bot
chat:write          - Send messages
channels:history    - Read channel messages
channels:read       - View channel info
users:read          - View user info
```

---

### Step 4: Install App to Workspace

1. Scroll to the top of **"OAuth & Permissions"** page
2. Click **"Install to Workspace"**
3. Review the permissions requested
4. Click **"Allow"**

You'll see a success message with your tokens.

---

### Step 5: Copy the Bot Token

After installation, you'll see two tokens:

**Bot User OAuth Token** (starts with `xoxb-`)
```
xoxb-1234567890-1234567890-EXAMPLE-DUMMY-TOKEN-NOT-REAL
```

**User OAuth Token** (starts with `xoxp-`)
```
xoxp-1234567890123-1234567890123-...
```

**⚠️ Important:** 
- Copy the **Bot User OAuth Token** (`xoxb-...`)
- This is the token you'll use with CloakCode
- Keep it secret - treat it like a password

---

### Step 6: Add Token to CloakCode

#### Option 1: Direct to .env file

```bash
# Edit .env file
nano .env

# Add this line:
SLACK_BOT_TOKEN=xoxb-your-actual-token-here
```

#### Option 2: Using the setup script

```bash
# The add-credential script will prompt you
./scripts/add-credential.sh

# Select: Slack
# Paste your token when prompted
```

---

### Step 7: Configure CloakCode Proxy

Add Slack strategy to `proxy/config.yaml`:

```yaml
strategies:
  - name: slack
    type: bearer
    config:
      token: SLACK_BOT_TOKEN
      dummy_pattern: "xoxb-DUMMY"
      allowed_hosts:
        - "slack.com"
        - "*.slack.com"

rules:
  - name: slack-injection
    domain_regex: "^(.*\\.)?slack\\.com$"
    trigger_header_regex: "xoxb-DUMMY"
    strategy: slack
    priority: 100
```

---

### Step 8: Test the Integration

#### Test 1: Basic Connection

```python
from slack_sdk import WebClient

# Use dummy token - will be replaced by proxy
client = WebClient(token="xoxb-DUMMY")

# Test API call
response = client.auth_test()
print(f"Connected as: {response['user']}")
```

#### Test 2: Send a Message

```python
from slack_sdk import WebClient

client = WebClient(token="xoxb-DUMMY")

# Send to a channel
response = client.chat_postMessage(
    channel="#general",
    text="Hello from CloakCode! 🚀"
)

print(f"Message sent: {response['ts']}")
```

#### Test 3: Verify Credential Injection

```bash
# On host machine - monitor the logs
tail -f logs/proxy_injections.log

# You should see:
# [2026-01-13 19:45:23] INJECTION: slack.com/api
#   Trigger: xoxb-DUMMY detected
#   Strategy: slack
#   Status: SUCCESS
```

---

## Slack App Token (Socket Mode)

### What is an App Token?

An **App Token** (starts with `xapp-`) is required for:
- **Socket Mode** - Real-time events without a public endpoint
- **App-level operations** - Managing the app itself
- **WebSocket connections** - Persistent connections to Slack

### When Do You Need It?

You need an App Token if you want to:
- Use Socket Mode instead of HTTP webhooks
- Receive real-time events without exposing a public URL
- Build apps that work behind firewalls
- Develop locally without ngrok/tunnels

### Step-by-Step: Get App Token

1. Go to your app in Slack API dashboard
2. Click **"Basic Information"** in sidebar
3. Scroll down to **"App-Level Tokens"**
4. Click **"Generate Token and Scopes"**
5. Enter token name: e.g., "Socket Mode Token"
6. Add scopes:
   - `connections:write` - Required for Socket Mode
   - `authorizations:read` - Optional, for app info
7. Click **"Generate"**
8. Copy the token (starts with `xapp-`)

### Add App Token to CloakCode

```bash
# Edit .env file
nano .env

# Add both tokens:
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
```

### Configure for Socket Mode

```yaml
strategies:
  # Bot Token for API calls
  - name: slack-bot
    type: bearer
    config:
      token: SLACK_BOT_TOKEN
      dummy_pattern: "xoxb-DUMMY"
      allowed_hosts:
        - "slack.com"
        - "*.slack.com"
  
  # App Token for Socket Mode
  - name: slack-app
    type: bearer
    config:
      token: SLACK_APP_TOKEN
      dummy_pattern: "xapp-DUMMY"
      allowed_hosts:
        - "slack.com"
        - "*.slack.com"

rules:
  # Bot Token injection
  - name: slack-bot-injection
    domain_regex: "^(.*\\.)?slack\\.com$"
    trigger_header_regex: "xoxb-DUMMY"
    strategy: slack-bot
    priority: 100
  
  # App Token injection
  - name: slack-app-injection
    domain_regex: "^(.*\\.)?slack\\.com$"
    trigger_header_regex: "xapp-DUMMY"
    strategy: slack-app
    priority: 100
```

### Enable Socket Mode

1. Go to **"Socket Mode"** in sidebar
2. Toggle **"Enable Socket Mode"** to On
3. Select your App-Level Token
4. Click **"Save Changes"**

### Socket Mode Example (Python)

```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Use dummy tokens - CloakCode injects real ones
app = App(token="xoxb-DUMMY")

@app.message("hello")
def message_hello(message, say):
    say(f"Hey there <@{message['user']}>!")

# Start Socket Mode
handler = SocketModeHandler(app, "xapp-DUMMY")
handler.start()
```

### Socket Mode Example (Node.js)

```javascript
const { App } = require('@slack/bolt');

// Use dummy tokens - CloakCode injects real ones
const app = new App({
  token: 'xoxb-DUMMY',
  appToken: 'xapp-DUMMY',
  socketMode: true
});

app.message('hello', async ({ message, say }) => {
  await say(`Hey there <@${message.user}>!`);
});

(async () => {
  await app.start();
  console.log('⚡️ Bolt app is running!');
})();
```

---

## Additional Configuration

### Enable Event Subscriptions (Optional)

For receiving events like new messages:

1. Go to **"Event Subscriptions"** in sidebar
2. Toggle **"Enable Events"** to On
3. Enter **Request URL**: `https://your-domain.com/slack/events`
4. Subscribe to bot events:
   - `message.channels` - Messages in public channels
   - `message.groups` - Messages in private channels
   - `message.im` - Direct messages
   - `app_mention` - When bot is mentioned
5. Click **"Save Changes"**

### Enable Interactive Components (Optional)

For buttons and interactive messages:

1. Go to **"Interactivity & Shortcuts"** in sidebar
2. Toggle **"Interactivity"** to On
3. Enter **Request URL**: `https://your-domain.com/slack/interactive`
4. Click **"Save Changes"**

### Add Slash Commands (Optional)

For custom `/commands`:

1. Go to **"Slash Commands"** in sidebar
2. Click **"Create New Command"**
3. Enter command: `/cloakcode`
4. Enter Request URL: `https://your-domain.com/slack/commands`
5. Add short description and usage hint
6. Click **"Save"**

---

## Security Best Practices

### Token Storage

✅ **DO:**
- Store token in `.env` file (git-ignored)
- Use environment variables
- Rotate tokens periodically
- Use CloakCode proxy for injection

❌ **DON'T:**
- Commit token to git
- Share token in chat/email
- Hardcode in source code
- Use in client-side code

### Token Permissions

- Grant **minimum necessary scopes**
- Review permissions regularly
- Create separate bots for different purposes
- Document why each scope is needed

### Monitoring

- Monitor `logs/proxy_injections.log` for usage
- Check Slack app dashboard for API calls
- Set up alerts for suspicious activity
- Review workspace audit logs

---

## Troubleshooting

### Error: "invalid_auth"

**Problem:** Token is invalid or revoked

**Solutions:**
1. Check token format (should start with `xoxb-`)
2. Verify token in Slack API dashboard
3. Reinstall app to workspace if needed
4. Generate new token

### Error: "not_in_channel"

**Problem:** Bot not invited to channel

**Solutions:**
1. Invite bot to channel: `/invite @CloakCode Bot`
2. Add `chat:write.public` scope to send without invitation
3. Check channel privacy settings

### Error: "missing_scope"

**Problem:** Bot lacks required permission

**Solutions:**
1. Go to Slack API dashboard
2. Add required scope under "OAuth & Permissions"
3. Reinstall app to workspace
4. Update token in `.env` file

### Token Not Being Injected

**Problem:** Proxy not replacing dummy token

**Solutions:**
1. Check `proxy/config.yaml` has Slack strategy
2. Verify dummy pattern matches: `xoxb-DUMMY`
3. Restart proxy: `docker-compose restart proxy`
4. Check logs: `docker logs cloakcode_proxy`

---

## Token Rotation

It's good security practice to rotate tokens periodically:

### How to Rotate

1. Go to Slack API dashboard
2. Navigate to **"OAuth & Permissions"**
3. Click **"Revoke" next to existing token**
4. Click **"Reinstall to Workspace"**
5. Copy new token
6. Update `.env` file
7. Restart proxy: `docker-compose restart proxy`

### When to Rotate

- **Regularly:** Every 90 days
- **Immediately if:**
  - Token accidentally exposed
  - Suspicious activity detected
  - Team member with access leaves
  - Security breach suspected

---

## Advanced: Multiple Workspaces

If you need to support multiple Slack workspaces:

```yaml
strategies:
  - name: slack-workspace-1
    type: bearer
    config:
      token: SLACK_BOT_TOKEN_WORKSPACE_1
      dummy_pattern: "xoxb-DUMMY-WS1"
      allowed_hosts:
        - "slack.com"
        - "*.slack.com"

  - name: slack-workspace-2
    type: bearer
    config:
      token: SLACK_BOT_TOKEN_WORKSPACE_2
      dummy_pattern: "xoxb-DUMMY-WS2"
      allowed_hosts:
        - "slack.com"
        - "*.slack.com"

rules:
  - name: slack-ws1-injection
    domain_regex: "^(.*\\.)?slack\\.com$"
    trigger_header_regex: "xoxb-DUMMY-WS1"
    strategy: slack-workspace-1
    priority: 100

  - name: slack-ws2-injection
    domain_regex: "^(.*\\.)?slack\\.com$"
    trigger_header_regex: "xoxb-DUMMY-WS2"
    strategy: slack-workspace-2
    priority: 100
```

---

## Code Examples

### Python (slack-sdk)

```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Use dummy token - CloakCode will inject real one
client = WebClient(token="xoxb-DUMMY")

try:
    # Post message
    response = client.chat_postMessage(
        channel="#general",
        text="Hello World!"
    )
    print(f"Message sent: {response['ts']}")
    
    # Upload file
    response = client.files_upload(
        channels="#general",
        file="document.pdf",
        title="Important Document"
    )
    print(f"File uploaded: {response['file']['id']}")
    
except SlackApiError as e:
    print(f"Error: {e.response['error']}")
```

### Node.js (@slack/web-api)

```javascript
const { WebClient } = require('@slack/web-api');

// Use dummy token - CloakCode will inject real one
const client = new WebClient('xoxb-DUMMY');

async function postMessage() {
  try {
    const result = await client.chat.postMessage({
      channel: '#general',
      text: 'Hello from Node.js!'
    });
    console.log(`Message sent: ${result.ts}`);
  } catch (error) {
    console.error(`Error: ${error.message}`);
  }
}

postMessage();
```

### cURL

```bash
# Use dummy token - CloakCode will inject real one
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer xoxb-DUMMY" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "#general",
    "text": "Hello from cURL!"
  }'
```

---

## Resources

- **Slack API Documentation**: https://api.slack.com/
- **Bot Users Guide**: https://api.slack.com/bot-users
- **OAuth Scopes Reference**: https://api.slack.com/scopes
- **slack-sdk for Python**: https://slack.dev/python-slack-sdk/
- **@slack/web-api for Node**: https://slack.dev/node-slack-sdk/

---

## Quick Reference

| Item | Value/Location |
|------|----------------|
| **Dashboard URL** | https://api.slack.com/apps |
| **Token Format** | `xoxb-XXXX-XXXX-XXXX` |
| **Token Location** | OAuth & Permissions page |
| **Dummy Pattern** | `xoxb-DUMMY` |
| **Env Variable** | `SLACK_BOT_TOKEN` |
| **Test Endpoint** | https://slack.com/api/auth.test |

---

## Support

If you encounter issues:
1. Check Slack API dashboard for errors
2. Review `logs/proxy_injections.log`
3. Test with Slack API tester: https://api.slack.com/methods/auth.test/test
4. Consult Slack community: https://slackcommunity.com/

---

**Last Updated:** 2026-01-13  
**Version:** 1.0
