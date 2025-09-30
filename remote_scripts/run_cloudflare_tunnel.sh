#!/bin/bash
set -e

# Default port
DEFAULT_PORT=8188
PORT=${1:-$DEFAULT_PORT}

echo "=== Starting Cloudflare Tunnel ==="
echo "Port: $PORT"
echo "Local URL: http://localhost:$PORT"

# Verify cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Error: cloudflared not found. Please run install_cloudflared.sh first."
    exit 1
fi

# Check if port is valid
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: Invalid port number. Must be between 1-65535."
    exit 1
fi

echo ""
echo "Starting TryCloudflare tunnel..."
echo "This will create a random subdomain on trycloudflare.com"
echo "Press Ctrl+C to stop the tunnel"
echo ""

# Start the tunnel
cloudflared tunnel --url "http://localhost:$PORT"