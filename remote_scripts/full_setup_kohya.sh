#!/bin/bash
set -e

echo "=========================================="
echo "Starting full Kohya_SS setup..."
echo "This will install:"
echo "  - System dependencies"
echo "  - CUDA 12.8 toolkit"
echo "  - Kohya_SS from GitHub"
echo "  - Python virtual environment"
echo "=========================================="

# Run miniforge installation
echo "Installing Miniforge..."
/home/ubuntu/remote_scripts/install_miniforge.sh

# Run kohya environment setup
echo "Setting up Kohya_SS environment..."
/home/ubuntu/remote_scripts/setup_kohya_env.sh

# Install cloudflared for tunneling
echo "Installing Cloudflare tunnel..."
/home/ubuntu/remote_scripts/install_cloudflared.sh

echo "=========================================="
echo "Full Kohya_SS setup complete!"
echo "=========================================="
echo ""
echo "Environment ready with:"
echo "  ✓ Miniforge conda distribution"
echo "  ✓ System dependencies (Python 3.11, Git)"
echo "  ✓ CUDA 12.8 toolkit"
echo "  ✓ Kohya_SS training environment"
echo "  ✓ Cloudflare tunnel for external access"
echo ""
echo "To start Kohya_SS GUI:"
echo "  cd /home/ubuntu/kohya_ss"
echo "  ./gui.sh --listen 0.0.0.0 --server_port 7860"
echo ""
echo "To start with tunnel:"
echo "  python local_scripts/start_tunnel.py -i <instance_id> -p 7860"