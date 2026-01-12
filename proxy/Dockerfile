# Universal API Credential Injector - Proxy Container
# Based on mitmproxy for credential injection and traffic inspection
# v2.0 - Strategy-based architecture with AWS SigV4 support

FROM mitmproxy/mitmproxy:10.1.1

# Install iptables for transparent proxy mode
USER root
RUN apt-get update && apt-get install -y iptables && rm -rf /var/lib/apt/lists/*

# Install additional Python packages for enhanced functionality
RUN pip install --no-cache-dir \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1 \
    boto3==1.34.0 \
    botocore==1.34.0

# Create directory for proxy scripts and strategies
RUN mkdir -p /app/strategies

# Copy strategy modules first (required by inject.py)
COPY strategies/ /app/strategies/

# Copy the main injection script
COPY inject.py /app/inject.py

# Copy example configuration
COPY config.yaml.example /app/config.yaml.example

# Make script executable
RUN chmod +x /app/inject.py

# Create directory for certificates (shared with agent)
RUN mkdir -p /certs

# Expose proxy port
EXPOSE 8080

# Health check to ensure proxy is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD mitmdump --version || exit 1

# Set working directory
WORKDIR /app

# Run mitmproxy with the injection script
# --set block_global=false: Allow all traffic (we filter in script)
# --set ssl_insecure=true: Accept upstream SSL certs (for dev/testing)
# --set confdir=/certs: Store generated certs in shared volume
CMD ["mitmdump", \
     "--set", "confdir=/certs", \
     "--set", "ssl_insecure=true", \
     "--set", "block_global=false", \
     "--listen-host", "0.0.0.0", \
     "--listen-port", "8080", \
     "-s", "/app/inject.py"]
