#!/bin/bash
# Build and run env-sidecar in Docker

echo "🔨 Building env-sidecar Docker image..."
docker build -f Dockerfile.sidecar -t env-sidecar:latest .

echo "🚀 Starting env-sidecar container..."
docker run -d \
  --name env-sidecar \
  --restart unless-stopped \
  -p 8888:8888 \
  -v "$(pwd)/sidecar.json:/etc/sidecar/sidecar.json:ro" \
  -v "$(pwd)/.env.vault:/etc/sidecar/.env.vault:ro" \
  env-sidecar:latest

echo ""
echo "✅ env-sidecar is running!"
echo ""
echo "📍 Use this URL in your devcontainer .env:"
echo "   ANTHROPIC_BASE_URL=http://host.docker.internal:8888/anthropic"
echo ""
echo "📋 View logs: docker logs -f env-sidecar"
echo "🛑 Stop: docker stop env-sidecar"
echo "🔄 Restart: docker restart env-sidecar"
