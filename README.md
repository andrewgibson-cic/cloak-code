# env-sidecar

🛡️ A transparent HTTP/HTTPS proxy that securely injects API credentials for AI Coding Agents and development environments.

## What is env-sidecar?

env-sidecar is a standalone transparent proxy that allows AI coding agents (and developers) to make API calls to services like OpenAI, Anthropic, Stripe, etc. **without ever exposing the actual API keys** in the agent's environment or source code.

### How it works (Transparent Proxy Mode)

1. **Transparent Proxy**: Clients use standard HTTP proxy environment variables (`http_proxy`, `https_proxy`)
2. **MITM TLS**: Terminates TLS with a self-generated CA certificate
3. **Domain-Based Routing**: Injects credentials based on the target domain
4. **Credential Injection**: Automatically adds `Authorization` and other headers to requests
5. **Certificate Distribution**: Serves CA certificate via magic domain (`mitm.it`)

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Client         │ ──────> │ env-sidecar      │ ──────> │ Target API       │
│  (AI Agent)      │  HTTP   │  (MITM Proxy)    │  HTTPS  │ (api.anthropic)  │
│                  │ Proxy   │                  │ Request │                  │
│ No API Keys!     │ Request │ Has API Keys     │         │                  │
│                  │         │ Injects Headers  │         │                  │
└──────────────────┘         └──────────────────┘         └──────────────────┘
       ^                             ^                           |
       |                             |                           v
       └─────────────────────────────┴───────────────────────────┘
                          Secure Response
```

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

Example `.env.vault`:
```
ANTHROPIC_AUTH_TOKEN=sk-ant-your-real-key
OPENAI_API_KEY=sk-your-openai-key
HF_TOKEN=hf_your_huggingface_token
```

### 2. Create your configuration (`sidecar.json`)

```bash
cp sidecar.json.example sidecar.json
# Edit sidecar.json to configure your domains
```

### 3. Run the proxy

```bash
./env-sidecar --verbose
```

## Configuration

### Config file structure (`sidecar.json`)

```json
{
  "port": 8888,
  "env_file": ".env.vault",
  "ca": {
    "cert_path": "certs/ca.crt",
    "key_path": "certs/ca.key"
  },
  "domains": {
    "api.anthropic.com": {
      "inject_headers": {
        "Authorization": "Bearer ${ANTHROPIC_AUTH_TOKEN}",
        "anthropic-version": "2023-06-01"
      }
    },
    "api.openai.com": {
      "inject_headers": {
        "Authorization": "Bearer ${OPENAI_API_KEY}"
      }
    }
  }
}
```

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `port` | integer | No | Port to listen on (default: 8888) |
| `env_file` | string | No | Path to environment file (default: `.env.vault`) |
| `ca.cert_path` | string | No | Path to CA certificate (default: `certs/ca.crt`) |
| `ca.key_path` | string | No | Path to CA private key (default: `certs/ca.key`) |
| `domains` | object | Yes | Map of domain to header injection rules |

### Domain Configuration

Each domain entry specifies which headers to inject:

#### Option 1: Inject Headers (precise control)

```json
{
  "api.anthropic.com": {
    "inject_headers": {
      "Authorization": "Bearer ${ANTHROPIC_AUTH_TOKEN}",
      "anthropic-version": "2023-06-01"
    }
  }
}
```

**Variable Expansion:** `${VAR_NAME}` expands to the value from your `.env.vault` file.

#### Option 2: Replace Values (flexible scanning)

```json
{
  "api.openai.com": {
    "replace_values": ["OPENAI_API_KEY"]
  },
  "huggingface.co": {
    "replace_values": ["HF_TOKEN"],
    "replace_in_headers": ["Authorization"]
  }
}
```

**Replace Values**: Scans all request headers (or specific headers if `replace_in_headers` is set) and replaces placeholder values with real credentials. For example, if the client sends:
- `Authorization: Bearer OPENAI_API_KEY`
- `x-api-key: HF_TOKEN`

The proxy replaces `OPENAI_API_KEY` and `HF_TOKEN` with the real values from your `.env.vault`. This is useful when you don't know the exact authorization scheme (Bearer, Basic, token, etc.).

**Security Tip**: Use `replace_in_headers` to restrict scanning to only specific headers, reducing the risk of accidental replacements.

## Usage

### Command-line options

```bash
# Run with default config
./env-sidecar

# Use custom config file
./env-sidecar --config /path/to/config.json

# Override port
./env-sidecar --port 9090

# Enable verbose logging
./env-sidecar --verbose

# Generate CA certificate only
./env-sidecar --generate-ca
```

### Using with a Client

Configure your client to use the HTTP proxy:

**Environment variables:**
```bash
export http_proxy=http://127.0.0.1:8888
export https_proxy=http://127.0.0.1:8888
export no_proxy=localhost,127.0.0.1
```

**Python requests:**
```python
import os
import requests

os.environ['http_proxy'] = 'http://127.0.0.1:8888'
os.environ['https_proxy'] = 'http://127.0.0.1:8888'

# Requests will be transparently proxied with credentials injected
response = requests.get("https://api.anthropic.com/v1/messages", ...)
```

**curl:**
```bash
curl -x http://127.0.0.1:8888 https://api.anthropic.com/v1/messages
```

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
  -v "$(pwd)/certs:/etc/sidecar/certs" \
  env-sidecar:latest
```

### Access from other containers

Other containers on the `sidecar-network` can access the proxy by setting:

```bash
http_proxy=http://env-sidecar:8888
https_proxy=http://env-sidecar:8888
```

## Devcontainer Setup

To use env-sidecar with a VS Code devcontainer:

1. **Configure network and proxy settings in devcontainer.json:**
   ```json
   {
     "runArgs": ["--network", "sidecar-network"],
     "containerEnv": {
       "http_proxy": "http://env-sidecar:8888",
       "https_proxy": "http://env-sidecar:8888",
       "no_proxy": "localhost,127.0.0.1,env-sidecar"
     },
     "postCreateCommand": "bash .devcontainer/setup-cert.sh"
   }
   ```

2. **The `setup-cert.sh` script will:**
   - Download the CA certificate from the proxy
   - Install it in the container's trust store
   - Enable transparent HTTPS proxying

3. **Rebuild and reopen the devcontainer**

After setup, all HTTP/HTTPS traffic will be transparently proxied with credentials automatically injected.

## CA Certificate Management

### Automatic Generation

The proxy automatically generates a CA certificate on first run if one doesn't exist.

### Manual Generation

```bash
./env-sidecar --generate-ca
```

### Installing the CA Certificate

**Linux/Devcontainer (via magic domain):**
```bash
curl -x http://127.0.0.1:8888 http://mitm.it/cert/pem -o /tmp/ca.crt
sudo cp /tmp/ca.crt /usr/local/share/ca-certificates/env-sidecar-ca.crt
sudo update-ca-certificates
```

**macOS:**
```bash
curl -x http://127.0.0.1:8080 http://mitm.it/cert/pem -o env-sidecar-ca.crt
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain env-sidecar-ca.crt
```

### Magic Domain

The proxy serves its CA certificate via the special domain `mitm.it` (accessible through the proxy):

- `http://mitm.it/` - HTML page with download links
- `http://mitm.it/cert/pem` - Download PEM format
- `http://mitm.it/cert/crt` - Download CRT format

## Examples

### Anthropic API

**`.env.vault`:**
```
ANTHROPIC_AUTH_TOKEN=sk-ant-your-real-key
```

**`sidecar.json`:**
```json
{
  "domains": {
    "api.anthropic.com": {
      "inject_headers": {
        "Authorization": "Bearer ${ANTHROPIC_AUTH_TOKEN}",
        "anthropic-version": "2023-06-01"
      }
    }
  }
}
```

### Multiple APIs

```json
{
  "domains": {
    "api.anthropic.com": {
      "inject_headers": {
        "Authorization": "Bearer ${ANTHROPIC_AUTH_TOKEN}",
        "anthropic-version": "2023-06-01"
      }
    },
    "api.openai.com": {
      "replace_values": ["OPENAI_API_KEY"]
    },
    "huggingface.co": {
      "replace_values": ["HF_TOKEN"]
    }
  }
}
```

### Using replace_values for flexible auth

The `replace_values` option is useful when clients may send different authorization schemes:

**Client sends:**
```bash
# Any of these will work - the placeholder gets replaced:
curl -x http://127.0.0.1:8080 https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer OPENAI_API_KEY"

curl -x http://127.0.0.1:8080 https://api.openai.com/v1/chat/completions \
  -H "Authorization: OPENAI_API_KEY"

curl -x http://127.0.0.1:8080 https://api.openai.com/v1/chat/completions \
  -H "x-api-key: OPENAI_API_KEY"
```

**sidecar.json:**
```json
{
  "domains": {
    "api.openai.com": {
      "replace_values": ["OPENAI_API_KEY"]
    }
  }
}
```

## Security Features

- **Domain-Based Filtering**: Credentials only injected for configured domains
- **TLS Termination**: MITM proxy with self-signed CA certificate
- **Environment Variable Expansion**: API keys never appear in config files
- **Credential Isolation**: Each domain can have its own set of credentials
- **No Client Configuration**: Standard HTTP proxy protocol, no special client needed
- **Flexible Header Scanning**: `replace_values` scans for placeholders without needing to know exact auth schemes
- **Restricted Header Scanning**: Use `replace_in_headers` to limit scanning to specific headers for additional security

## Architecture Comparison

### Old: Path-Based Reverse Proxy
```
Client → http://localhost:8888/anthropic/v1/... → Proxy → api.anthropic.com
```
- Required client to know proxy URL
- Path-based routing
- No TLS handling

### New: Transparent Proxy
```
Client → https://api.anthropic.com/v1/... (via http_proxy) → Proxy → api.anthropic.com
```
- Client uses real URLs
- Domain-based routing
- Full TLS handling with CA certificate

## Troubleshooting

### Port already in use
```bash
# Check what's using the port
lsof -i :8888

# Use a different port
./env-sidecar --port 9090
```

### Certificate errors
- Ensure CA certificate is installed on the client
- Verify the proxy is running and accessible
- Check that `http_proxy` and `https_proxy` are set correctly

### Environment variables not expanding
- Ensure your `.env.vault` file exists and is readable
- Check that variable names match exactly (case-sensitive)
- Verify syntax: `${VAR_NAME}` (not `$VAR_NAME` or `{VAR_NAME}`)
- Use `--verbose` flag to see expansion warnings

### Connection refused from Docker container
- Ensure env-sidecar is running on the correct network
- Verify both containers are on the same Docker network
- Check that the container name is correct (`env-sidecar`)

## Development

### Build
```bash
go build -o env-sidecar
```

### Run with verbose logging
```bash
./env-sidecar --verbose
```

### Test
```bash
# Set proxy
export http_proxy=http://127.0.0.1:8888
export https_proxy=http://127.0.0.1:8888

# Test with curl (will have credentials injected)
curl https://api.anthropic.com/v1/messages \
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
