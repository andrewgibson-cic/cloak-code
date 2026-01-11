# Building env-sidecar

env-sidecar is distributed as a Go binary that runs inside a Docker container. You can build it using either the VS Code dev container or a Docker build container.

## Build Steps

### Option 1: VS Code Dev Container (Recommended)

Open the project in VS Code with the Dev Containers extension. When prompted, select "Reopen in Container".

The dev container includes Go 1.23.4 and all required tools. Build from inside the container:

```bash
./build.sh
```

The [`build.sh`](build.sh) script compiles the binary and copies configuration files to the [`env-sidecar/`](env-sidecar/) directory.

### Option 2: Docker Build Container

Build using Docker directly:

```bash
docker build --target builder -t env-sidecar-builder .
docker create --name builder env-sidecar-builder
docker cp builder:/build/env-sidecar ./env-sidecar/
docker rm builder
```

The `env-sidecar` executable is now located in the [`env-sidecar/`](env-sidecar/) directory.

### 2. Configure and Run

From the [`env-sidecar/`](env-sidecar/) directory, edit the configuration files:

* **[`.env.vault`](env-sidecar/.env.vault)** - Add your API credentials (e.g., `ANTHROPIC_AUTH_TOKEN`, `HF_TOKEN`)
* **[`sidecar.json`](env-sidecar/sidecar.json)** - Configure domains and header replacements

Start the proxy:

```bash
cd env-sidecar
docker compose up -d
```

The sidecar will:
* Generate a CA certificate on first run
* Listen on port `8888` for HTTP/HTTPS proxy connections
* Make the CA certificate available at `http://mitm.it/cert/pem` (via the proxy)

## Development Container Setup

When the sidecar is running, rebuild your dev container. The [`.devcontainer/setup-cert.sh`](.devcontainer/setup-cert.sh) post-create script will:

1. Download the CA certificate from the running sidecar
2. Install it into the system trust store
3. Enable tools like `curl`, `git`, and Python `requests` to work through the proxy

Verify the setup:

```bash
curl -v https://api.anthropic.com --proxy http://env-sidecar:8888
```

## Project Structure

```
.
├── build.sh                 # Build script for dev container
├── Dockerfile               # Dev container image
├── BUILD.md                 # This file
├── .devcontainer/
│   ├── devcontainer.json    # Dev container configuration
│   └── setup-cert.sh        # CA certificate bootstrap script
└── env-sidecar/
    ├── docker-compose.yml   # Sidecar service definition
    ├── Dockerfile.sidecar   # Minimal runtime image
    ├── sidecar.json         # Proxy configuration
    └── .env.vault           # Credential storage (not tracked)
```
