# SafeClaude Agent Container
# Provides an isolated, recoverable environment for Claude Code CLI

FROM node:20-bookworm

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install essential system packages and development tools
RUN apt-get update && apt-get install -y \
    # Core utilities
    curl \
    wget \
    git \
    vim \
    nano \
    jq \
    ca-certificates \
    gnupg \
    # Build tools for native modules
    build-essential \
    gcc \
    g++ \
    make \
    # Python (many tools require it)
    python3 \
    python3-pip \
    python3-venv \
    # SSL/TLS tools
    openssl \
    # Network utilities for debugging
    iputils-ping \
    net-tools \
    dnsutils \
    # Process management
    procps \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user 'claude' with UID 1000 (matches most Linux host users)
RUN useradd -m -u 1000 -s /bin/bash claude

# Grant passwordless sudo access to claude user
# This allows the agent to install packages autonomously
RUN apt-get update && apt-get install -y sudo \
    && echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code@latest

# Create workspace directory
RUN mkdir -p /home/claude/workspace && chown -R claude:claude /home/claude/workspace

# Create config directory for persistent authentication
RUN mkdir -p /home/claude/.config/claude-code && chown -R claude:claude /home/claude/.config

# Create certificates directory
RUN mkdir -p /usr/local/share/ca-certificates && chmod 755 /usr/local/share/ca-certificates

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Switch to claude user
USER claude
WORKDIR /home/claude

# Configure proxy environment variables
# All traffic will be routed through the secure proxy
ENV HTTP_PROXY=http://proxy:8080
ENV HTTPS_PROXY=http://proxy:8080
ENV NO_PROXY=localhost,127.0.0.1

# Configure Node.js to trust custom CA certificates
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/mitmproxy-ca-cert.pem

# Configure Python requests to trust custom CA certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Set dummy API keys (will be replaced by proxy)
ENV OPENAI_API_KEY=DUMMY_OPENAI_KEY
ENV GITHUB_TOKEN=DUMMY_GITHUB_TOKEN
ENV ANTHROPIC_API_KEY=DUMMY_ANTHROPIC_KEY
ENV AWS_ACCESS_KEY_ID=DUMMY_AWS_ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY=DUMMY_AWS_SECRET_KEY

# Health check to ensure container is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD node --version || exit 1

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command: start interactive bash shell
CMD ["/bin/bash"]
