# Adding New API Credentials to SafeClaude

SafeClaude now supports **ANY API credential** through its universal configuration system! This guide shows you how to add support for new APIs like Binance, eBay, Shopify, Coinbase, or literally any service.

## 🎯 Overview

The system has been redesigned to be **configuration-driven** rather than code-driven. This means:

- ✅ **No code changes needed** - just edit YAML configuration
- ✅ **No container rebuilds** - changes take effect on restart
- ✅ **Flexible authentication** - supports headers, query params, multiple formats
- ✅ **Security maintained** - strict host whitelisting per credential
- ✅ **Easy management** - CLI tools to help you add credentials

## 🚀 Quick Start

### Option 1: Use the Interactive Wizard (Recommended)

```bash
./scripts/add-credential.sh
```

The wizard will guide you through:
1. Service information
2. Token configuration
3. Authentication method
4. Host whitelist
5. Documentation URL

### Option 2: Manual Configuration

If you prefer manual editing, follow these steps:

## 📝 Step-by-Step Manual Setup

### Step 1: Add Configuration to `credentials.yml`

Open `credentials.yml` and add your service configuration:

```yaml
credentials:
  # ... existing credentials ...
  
  # Your New Service
  myservice:
    display_name: "MyService API"
    dummy_token: "DUMMY_MYSERVICE_KEY"
    env_var: "REAL_MYSERVICE_API_KEY"
    header_locations:
      - name: "Authorization"
        format: "Bearer {token}"
    allowed_hosts:
      - "api.myservice.com"
      - "*.myservice.com"
    docs_url: "https://myservice.com/docs/api-keys"
```

### Step 2: Add Real Credential to `.env`

Open your `.env` file (create from `.env.template` if needed):

```bash
# MyService API
# Get from: https://myservice.com/docs/api-keys
REAL_MYSERVICE_API_KEY=your-actual-api-key-here
```

⚠️ **NEVER commit `.env` to version control!** It's already in `.gitignore`.

### Step 3: Restart the Proxy

```bash
docker-compose restart proxy
```

That's it! Your credential is now available to the agent.

## 📖 Configuration Reference

### Complete Configuration Schema

```yaml
credentials:
  service_name:
    # Display name shown in logs
    display_name: "Human-Readable Service Name"
    
    # Dummy token the agent uses (never sees the real one)
    dummy_token: "DUMMY_SERVICE_KEY"
    
    # Environment variable containing the real credential
    env_var: "REAL_SERVICE_API_KEY"
    
    # Where to inject the credential (can have multiple)
    header_locations:
      - name: "Authorization"        # Header name
        format: "Bearer {token}"     # Format template
      - name: "X-API-Key"
        format: "{token}"
    
    # Query parameters (optional)
    query_param_names:
      - "api_key"
      - "token"
    
    # SECURITY: Whitelist of allowed hosts (REQUIRED)
    allowed_hosts:
      - "api.example.com"            # Exact match
      - "*.example.com"              # Wildcard subdomain
      - "example.com"                # Matches subdomains too
    
    # Link to API documentation (optional but recommended)
    docs_url: "https://example.com/docs/api"
    
    # Special handling flags (optional)
    requires_signature: false        # For APIs needing HMAC signing
```

## 🔐 Authentication Methods

### 1. Bearer Token (Most Common)

**Example:** OpenAI, Stripe, many REST APIs

```yaml
header_locations:
  - name: "Authorization"
    format: "Bearer {token}"
```

### 2. Custom Header

**Example:** Binance, custom APIs

```yaml
header_locations:
  - name: "X-MBX-APIKEY"
    format: "{token}"
```

### 3. Basic Auth Format

**Example:** Twilio, some legacy APIs

```yaml
header_locations:
  - name: "Authorization"
    format: "Basic {token}"
```

### 4. Token Prefix

**Example:** GitHub

```yaml
header_locations:
  - name: "Authorization"
    format: "token {token}"
```

### 5. Bot Token

**Example:** Discord

```yaml
header_locations:
  - name: "Authorization"
    format: "Bot {token}"
```

### 6. Query Parameters

**Example:** Some webhooks, legacy APIs

```yaml
query_param_names:
  - "api_key"
  - "access_token"
```

### 7. Multiple Methods

Some APIs support multiple authentication methods:

```yaml
header_locations:
  - name: "Authorization"
    format: "token {token}"
  - name: "X-GitHub-Token"
    format: "{token}"
query_param_names:
  - "access_token"
```

## 🛡️ Host Whitelisting (Security)

The host whitelist is **CRITICAL** for security. It prevents credentials from being sent to unauthorized destinations.

### Exact Match

```yaml
allowed_hosts:
  - "api.example.com"  # Only api.example.com
```

### Subdomain Wildcard

```yaml
allowed_hosts:
  - "*.example.com"    # Matches api.example.com, cdn.example.com, etc.
  - "example.com"      # Also matches www.example.com, api.example.com
```

### Multiple Hosts

```yaml
allowed_hosts:
  - "api.example.com"
  - "api-eu.example.com"
  - "api-us.example.com"
  - "sandbox.example.com"
```

### AWS Services (Special Case)

```yaml
allowed_hosts:
  - "*.amazonaws.com"   # Matches all AWS service endpoints
```

## 💡 Real-World Examples

### Example 1: Coinbase API

```yaml
coinbase:
  display_name: "Coinbase API"
  dummy_token: "DUMMY_COINBASE_KEY"
  env_var: "REAL_COINBASE_API_KEY"
  header_locations:
    - name: "CB-ACCESS-KEY"
      format: "{token}"
  allowed_hosts:
    - "api.coinbase.com"
    - "api.pro.coinbase.com"
  docs_url: "https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-key-authentication"
```

```bash
# .env
REAL_COINBASE_API_KEY=organizations/your-org-id/apiKeys/your-key-id
```

### Example 2: Shopify Admin API

```yaml
shopify:
  display_name: "Shopify Admin API"
  dummy_token: "DUMMY_SHOPIFY_TOKEN"
  env_var: "REAL_SHOPIFY_ACCESS_TOKEN"
  header_locations:
    - name: "X-Shopify-Access-Token"
      format: "{token}"
  allowed_hosts:
    - "*.myshopify.com"
  docs_url: "https://shopify.dev/docs/api/admin-rest#authentication"
```

```bash
# .env
REAL_SHOPIFY_ACCESS_TOKEN=shpat_your-access-token-here
```

### Example 3: SendGrid Email API

```yaml
sendgrid:
  display_name: "SendGrid API"
  dummy_token: "DUMMY_SENDGRID_KEY"
  env_var: "REAL_SENDGRID_API_KEY"
  header_locations:
    - name: "Authorization"
      format: "Bearer {token}"
  allowed_hosts:
    - "api.sendgrid.com"
  docs_url: "https://app.sendgrid.com/settings/api_keys"
```

```bash
# .env
REAL_SENDGRID_API_KEY=SG.your-sendgrid-api-key-here
```

### Example 4: Kraken Cryptocurrency Exchange

```yaml
kraken:
  display_name: "Kraken API"
  dummy_token: "DUMMY_KRAKEN_KEY"
  env_var: "REAL_KRAKEN_API_KEY"
  header_locations:
    - name: "API-Key"
      format: "{token}"
  allowed_hosts:
    - "api.kraken.com"
  docs_url: "https://docs.kraken.com/rest/#section/Authentication"
  requires_signature: true
```

## 🔍 Debugging & Verification

### View Configured Credentials

```bash
./scripts/list-credentials.sh
```

This shows:
- All configured services
- Which ones have credentials in `.env`
- Allowed hosts for each service
- Quick reference commands

### Enable Verbose Logging

Edit `credentials.yml`:

```yaml
security:
  verbose_logging: true
```

Restart and check proxy logs:

```bash
docker-compose restart proxy
docker-compose logs -f proxy
```

### Test a New Credential

1. **Add the configuration** (credentials.yml + .env)
2. **Restart proxy**: `docker-compose restart proxy`
3. **Check logs**: `docker-compose logs proxy | grep "Loaded"`
4. **Make a test request** from the agent container
5. **Verify injection**: Look for `✓ [Service] credential injected` in logs

## 🚨 Common Issues

### Issue: "Credential not configured" Error

**Cause:** Environment variable not set or contains placeholder text

**Fix:**
```bash
# Check your .env file
cat .env | grep REAL_MYSERVICE

# Make sure it's not a placeholder like "your-key-here"
REAL_MYSERVICE_API_KEY=actual-real-key-value
```

### Issue: "Host not whitelisted" Error

**Cause:** Request destination not in `allowed_hosts`

**Fix:** Add the host to the whitelist in `credentials.yml`:
```yaml
allowed_hosts:
  - "api.example.com"
  - "new-endpoint.example.com"  # Add this
```

### Issue: Credential Not Being Injected

**Checklist:**
1. ✅ Configuration added to `credentials.yml`
2. ✅ Real credential added to `.env`
3. ✅ Proxy container restarted
4. ✅ Dummy token matches exactly
5. ✅ Header name matches API documentation
6. ✅ Host is in whitelist

## 🔒 Security Best Practices

1. **Always use host whitelisting** - Never use `allowed_hosts: ["*"]`
2. **Principle of least privilege** - Only whitelist the exact hosts needed
3. **Never commit .env** - It's already in `.gitignore`, keep it that way
4. **Use read-only API keys** when possible
5. **Rotate credentials regularly**
6. **Monitor proxy logs** for suspicious activity

## 📚 Additional Resources

- **List credentials**: `./scripts/list-credentials.sh`
- **Add credential**: `./scripts/add-credential.sh`
- **View logs**: `docker-compose logs -f proxy`
- **Configuration file**: `credentials.yml`
- **Secrets file**: `.env` (never commit!)

## 🆘 Need Help?

If you're stuck:

1. Check the logs: `docker-compose logs proxy`
2. Run: `./scripts/list-credentials.sh`
3. Review existing configurations in `credentials.yml` as examples
4. Ensure your API documentation matches your configuration

---

**Remember:** With this system, you can add support for **ANY API** that uses HTTP authentication, without touching a single line of Python code! 🎉
