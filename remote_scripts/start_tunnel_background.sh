#!/bin/bash
set -e

# Default port
DEFAULT_PORT=8188
PORT=${1:-$DEFAULT_PORT}
SESSION_NAME=${2:-"cloudflare-tunnel"}

echo "=== Starting Cloudflare Tunnel in Background ==="
echo "Port: $PORT"
echo "Tmux session: $SESSION_NAME"

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

# Check if tmux session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Tmux session '$SESSION_NAME' already exists."
    echo "To view: tmux attach -t $SESSION_NAME"
    echo "To kill: tmux kill-session -t $SESSION_NAME"
    exit 1
fi

echo ""
echo "Starting tunnel in tmux session '$SESSION_NAME'..."

# Create tmux session and run cloudflared
tmux new-session -d -s "$SESSION_NAME" \
    "cloudflared tunnel --url http://localhost:$PORT"

echo ""
echo "Tunnel started in background!"
echo ""
echo "Commands:"
echo "  View tunnel:  tmux attach -t $SESSION_NAME"
echo "  Kill tunnel:  tmux kill-session -t $SESSION_NAME"
echo "  List sessions: tmux list-sessions"
echo ""
echo "The tunnel URL will be displayed in the tmux session."
echo "Wait a few seconds, then run: tmux capture-pane -t $SESSION_NAME -p"