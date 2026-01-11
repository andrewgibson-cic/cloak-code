# env-sidecar

🛡️ A lightweight reverse proxy that securely injects API credentials for AI Coding Agents and development environments.

## What is env-sidecar?

env-sidecar is a standalone local reverse proxy that allows AI coding agents (and developers) to make API calls to services like OpenAI, Anthropic, Stripe, etc. **without ever exposing the actual API keys** in the agent's environment or source code.

### How it works

1. **Local Proxy**: Runs on your localhost (127.0.0.1) or in a Docker container
2. **Secure Secrets**: Loads real API keys from your secure `.env.vault` file
3. **Header Sanitization**: Strips any Authorization headers sent by the client
4. **Secure Forwarding**: Injects real Authorization headers and forwards requests to target APIs
5. **Response Relay**: Returns API responses back to the client

## Installation

### Build from source

```bash
go build -o env-sidecar
```

### Using Go install

```bash
go install github.com/env-sidecar/env-sidecar@latest
```

## Quick Start

### 1. Create your secrets file (`.env.vault`)

```bash
cp .env.vault.example .env.vault
# Edit .env.vault and add your real API keys
```

### 2. Create your configuration (`sidecar.json`)

```bash
cp sidecar.json.example sidecar.json
# Edit sidecar.json to configure your proxy routes
```

### 3. Run the proxy

```bash
./env-sidecar --unsafe
```

## Usage

### Basic usage

```bash
./env-sidecar
```

This will:
- Read configuration from `sidecar.json`
- Load secrets from `.env.vault`
- Start the proxy on `127.0.0.1:8888`

### Command-line options

```bash
# Use custom config file
./env-sidecar --config /path/to/custom.json

# Override port
./env-sidecar --port 8080

# Enable verbose logging
./env-sidecar --verbose

# Bind to all interfaces (required for Docker/container access)
./env-sidecar --unsafe
```

## Configuration

### Config file structure (`sidecar.json`)

```json
{
  "port": 8888,
  "env_file": ".env.vault",
  "routes": {
    "/anthropic": {
      "target": "https://api.anthropic.com",
      "replace_values": ["ANTHROPIC_AUTH_TOKEN"]
    }
  }
}
```

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `port` | integer | No | Port to listen on (default: 8888) |
| `env_file` | string | No | Path to environment file (default: `.env.vault`) |
| `routes` | object | Yes | Map of proxy routes |

#### Route Configuration

Each route maps a local path to a target API. You have two options for authentication:

**Option 1: `replace_values` (Recommended)**

Simply specify which environment variables to replace. The proxy will scan ALL incoming headers and replace any value matching the env var name with the real value from your `.env.vault`:

```json
{
  "/openai": {
    "target": "https://api.openai.com/v1",
    "replace_values": ["OPENAI_API_KEY", "OPENAI_ORG_ID"]
  }
}
```

The client sends headers with the env var name as the value:
```
Authorization: Bearer OPENAI_API_KEY
```

The proxy replaces `OPENAI_API_KEY` with the real value before forwarding.

**Option 2: `headers` (Explicit configuration)**

Manually specify which headers to inject. This is useful for static headers or when you need full control:

```json
{
  "/anthropic": {
    "target": "https://api.anthropic.com",
    "headers": {
      "Authorization": "Bearer ${ANTHROPIC_AUTH_TOKEN}",
      "anthropic-version": "2023-06-01"
    }
  }
}
```

**Variable Expansion:** `${VAR_NAME}` expands to the value from your `.env.vault` file.

## Docker Deployment

For use with devcontainers or other Dockerized environments:

### Build the image

```bash
docker build -f Dockerfile.sidecar -t env-sidecar:latest .
```

### Create shared network

```bash
docker network create sidecar-network
```

### Run the container

```bash
docker run -d --name env-sidecar --network sidecar-network -p 8888:8888 \
  -v "$(pwd)/sidecar.json:/etc/sidecar/sidecar.json:ro" \
  -v "$(pwd)/.env.vault:/etc/sidecar/.env.vault:ro" \
  env-sidecar:latest
```

### Access from other containers

Other containers on the `sidecar-network` can access the proxy using:

```bash
http://env-sidecar:8888/anthropic
```

## WSL2 Support

When running with `--unsafe` in WSL2, env-sidecar automatically detects WSL2 and displays connection URLs for Docker containers:

```
🛡️  env-sidecar running on 0.0.0.0:8888
----------------------------------------
Proxy Maps:
  /anthropic  -> https://api.anthropic.com

👉 Instructions for AI:
  "Set your Base URL to http://127.0.0.1:8888/anthropic"
  "  (from Docker): http://host.docker.internal:8888/anthropic"
  "  (from Docker): http://172.28.240.1:8888/anthropic"
```

## Devcontainer Setup

To use env-sidecar with a VS Code devcontainer:

1. Add `sidecar-network` to your devcontainer.json:
   ```json
   {
     "runArgs": ["--network", "sidecar-network"]
   }
   ```

2. Set your environment variables in `.devcontainer/.env`:
   ```bash
   ANTHROPIC_BASE_URL=http://env-sidecar:8888/anthropic
   ```

3. Rebuild and reopen the devcontainer

## Examples

### Anthropic API (using `replace_values`)

**`.env.vault`:**
```
ANTHROPIC_AUTH_TOKEN=sk-ant-your-real-key
```

**`sidecar.json`:**
```json
{
  "port": 8888,
  "env_file": ".env.vault",
  "routes": {
    "/anthropic": {
      "target": "https://api.anthropic.com",
      "replace_values": ["ANTHROPIC_AUTH_TOKEN"]
    }
  }
}
```

**How it works:** The AI agent sends `Authorization: Bearer ANTHROPIC_AUTH_TOKEN` and the proxy replaces `ANTHROPIC_AUTH_TOKEN` with the real key.

### Multiple APIs (OpenAI + Stripe)

```json
{
  "port": 8888,
  "env_file": ".env.vault",
  "routes": {
    "/openai": {
      "target": "https://api.openai.com/v1",
      "replace_values": ["OPENAI_API_KEY"]
    },
    "/stripe": {
      "target": "https://api.stripe.com/v1",
      "replace_values": ["STRIPE_SECRET_KEY"]
    }
  }
}
```

## Security Features

- **Localhost Binding (Default)**: Binds to `127.0.0.1` only - not accessible from other machines
- **Header Sanitization**: Automatically removes `Authorization` and `X-Api-Key` headers from incoming requests
- **Environment Variable Expansion**: API keys never appear in code or config files
- **Hop-by-Hop Header Removal**: Removes connection-specific headers to prevent injection attacks
- **X-Forwarded-* Removal**: Strips proxy headers that could cause issues with upstream APIs

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Client     │ ──────> │ env-sidecar  │ ──────> │ Target API   │
│  (AI Agent)  │  HTTP   │  (Proxy)     │  HTTPS  │ (OpenAI, etc)│
│              │ Request │              │ Request │              │
│ No API Keys! │         │ Has API Keys │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
       ^                         ^                         |
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

### Environment variables not expanding
- Ensure your `.env.vault` file exists and is readable
- Check that variable names match exactly (case-sensitive)
- Verify syntax: `${VAR_NAME}` (not `$VAR_NAME` or `{VAR_NAME}`)
- Use `--verbose` flag to see expansion warnings

### Connection refused from Docker container
- Ensure env-sidecar is running with `--unsafe` flag
- Verify both containers are on the same Docker network
- Check firewall settings

## Development

### Build
```bash
go build -o env-sidecar
```

### Run with verbose logging
```bash
./env-sidecar --verbose --unsafe
```

### Test
```bash
# Test with curl
curl -X POST http://127.0.0.1:8888/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":1024,"messages":[{"role":"user","content":"hi"}]}'
```

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Code follows Go best practices
- Security considerations are maintained
- Documentation is updated
