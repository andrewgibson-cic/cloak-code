# SafeClaude Proxy Container
# Based on mitmproxy for credential injection and traffic inspection

FROM mitmproxy/mitmproxy:10.1.1

# Install additional Python packages for enhanced functionality
RUN pip install --no-cache-dir \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1

# Create directory for proxy scripts
RUN mkdir -p /scripts

# Copy the credential injection script
COPY inject.py /scripts/inject.py

# Make script executable
RUN chmod +x /scripts/inject.py

# Create directory for certificates (shared with agent)
RUN mkdir -p /certs

# Expose proxy port
EXPOSE 8080

# Health check to ensure proxy is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD mitmdump --version || exit 1

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
     "-s", "/scripts/inject.py"]
