# env-sidecar

🛡️ A lightweight reverse proxy that acts as a security "Air Gap" for AI Coding Agents.

## What is env-sidecar?

env-sidecar is a standalone local reverse proxy that allows AI coding agents to make API calls (to OpenAI, Stripe, etc.) **without ever possessing the actual API keys** in their environment or code.

### How it works

1. **Man-in-the-Middle Proxy**: Runs on your localhost (127.0.0.1)
2. **Secure Secrets**: Loads real API keys from your secure `.env.vault` file
3. **Header Sanitization**: Strips any Authorization headers sent by the AI agent
4. **Secure Forwarding**: Injects real Authorization headers and forwards requests to target APIs
5. **Response Relay**: Returns API responses back to the AI agent

## Installation

### Build from source

```bash
git clone <repository>
cd env-sidecar
go build -o env-sidecar
```

### Using Go install

```bash
go install github.com/env-sidecar/env-sidecar@latest
```

## Configuration

### 1. Create your secrets file (`.env.vault`)

```bash
cp .env.example .env.vault
# Edit .env.vault and add your real API keys
```

### 2. Create your configuration (`sidecar.json`)

```bash
cp sidecar.json.example sidecar.json
# Edit sidecar.json to configure your proxy routes
```

### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `port` | integer | No | Port to listen on (default: 8888) |
| `env_file` | string | No | Path to environment file (default: `.env.vault`) |
| `routes` | object | Yes | Map of proxy routes |

#### Route Configuration

Each route maps a local path to a target API:

```json
{
  "/openai": {
    "target": "https://api.openai.com/v1",
    "headers": {
      "Authorization": "Bearer ${OPENAI_API_KEY}",
      "Organization": "${OPENAI_ORG_ID}"
    }
  }
}
```

**Supported Variables:**
- `${VAR_NAME}` - Expands to the value from your `.env.vault` file

## Usage

### Basic usage

```bash
./env-sidecar
```

This will:
- Read configuration from `sidecar.json`
- Load secrets from `.env.vault`
- Start the proxy on `127.0.0.1:8888`

### Advanced usage

```bash
# Use custom config file
./env-sidecar --config /path/to/custom.json

# Override port
./env-sidecar --port 8080

# Bind to all interfaces (NOT RECOMMENDED - use only in trusted networks)
./env-sidecar --unsafe
```

## Example Setup

### For OpenAI API

1. **Configure secrets** (`.env.vault`):
   ```
   OPENAI_API_KEY=sk-your-real-key
   OPENAI_ORG_ID=org-your-org-id
   ```

2. **Configure proxy** (`sidecar.json`):
   ```json
   {
     "port": 8888,
     "env_file": ".env.vault",
     "routes": {
       "/openai": {
         "target": "https://api.openai.com/v1",
         "headers": {
           "Authorization": "Bearer ${OPENAI_API_KEY}",
           "Organization": "${OPENAI_ORG_ID}"
         }
       }
     }
   }
   ```

3. **Start the proxy**:
   ```bash
   ./env-sidecar
   ```

4. **Output**:
   ```
   🛡️  env-sidecar running on 127.0.0.1:8888
   ----------------------------------------
   Proxy Maps:
     /openai  -> https://api.openai.com/v1

   👉 Instructions for AI:
     "Set your Base URL to http://127.0.0.1:8888/openai"
   ```

5. **Use with AI Agent**:
   Configure your AI agent to use base URL: `http://127.0.0.1:8888/openai`

   The AI will make requests to `http://127.0.0.1:8888/openai/chat/completions`
   which will be forwarded to `https://api.openai.com/v1/chat/completions` with your real API key.

### Multiple APIs (OpenAI + Stripe)

```json
{
  "port": 8888,
  "env_file": ".env.vault",
  "routes": {
    "/openai": {
      "target": "https://api.openai.com/v1",
      "headers": {
        "Authorization": "Bearer ${OPENAI_API_KEY}"
      }
    },
    "/stripe": {
      "target": "https://api.stripe.com/v1",
      "headers": {
        "Authorization": "Bearer ${STRIPE_SECRET_KEY}"
      }
    }
  }
}
```

Output:
```
🛡️  env-sidecar running on 127.0.0.1:8888
----------------------------------------
Proxy Maps:
  /openai  -> https://api.openai.com/v1
  /stripe  -> https://api.stripe.com/v1

👉 Instructions for AI:
  "Set your Base URL to http://127.0.0.1:8888/openai"
  "Set your Base URL to http://127.0.0.1:8888/stripe"
```

## Security Features

### 1. Localhost Binding (Default)
- **Binds to `127.0.0.1` only** - not accessible from other machines
- Requires `--unsafe` flag to bind to `0.0.0.0`

### 2. Header Sanitization
- Automatically removes `Authorization` headers from incoming requests
- Automatically removes `X-Api-Key` headers from incoming requests
- Prevents AI agents from overriding your secure credentials

### 3. Environment Variable Expansion
- API keys never appear in code or configuration files
- Keys stored only in your secure `.env.vault` file
- Variables expanded at runtime using `${VAR}` syntax

### 4. Hop-by-Hop Header Removal
- Removes connection-specific headers (Connection, Keep-Alive, etc.)
- Prevents header injection attacks

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   AI Agent   │ ──────> │ env-sidecar  │ ──────> │ Target API   │
│   (Client)   │  HTTP   │  (Proxy)     │  HTTPS  │ (OpenAI, etc)│
│              │ Request │              │ Request │              │
│ No API Keys! │         │ Has API Keys │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
       ^                         ^                         |
       |                         |                         |
       |                         |                         v
       └─────────────────────────┴─────────────────────────┘
                          Secure Response
```

## Troubleshooting

### Port already in use
```bash
# Check what's using the port
lsof -i :8888

# Use a different port
./env-sidecar --port 8889
```

### Configuration not found
```bash
# Specify custom config path
./env-sidecar --config /path/to/sidecar.json
```

### Environment variables not expanding
- Ensure your `.env.vault` file exists and is readable
- Check that variable names match exactly (case-sensitive)
- Verify syntax: `${VAR_NAME}` (not `$VAR_NAME` or `{VAR_NAME}`)

## Development

### Build
```bash
go build -o env-sidecar
```

### Run
```bash
./env-sidecar
```

### Test
```bash
# In another terminal, test with curl
curl -H "Authorization: fake-key" http://127.0.0.1:8888/openai/models
```

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Code follows Go best practices
- Security considerations are maintained
- Documentation is updated
