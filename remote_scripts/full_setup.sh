#!/bin/bash
set -e

echo "=== Full ComfyUI Setup Script ==="
echo "This script will install Miniforge, setup ComfyUI environment, and download models"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 1: Install Miniforge
echo ""
echo "Step 1/3: Installing Miniforge..."
bash "$SCRIPT_DIR/install_miniforge.sh"

# Source bashrc to get conda in PATH
echo "Sourcing bashrc to load conda..."
source "$HOME/.bashrc" || true

# Step 2: Setup ComfyUI environment
echo ""
echo "Step 2/3: Setting up ComfyUI environment..."
bash "$SCRIPT_DIR/setup_comfy_env.sh"

# Step 3: Download models
echo ""
echo "Step 3/3: Downloading ComfyUI models..."
bash "$SCRIPT_DIR/download_comfy_models.sh"

echo ""
echo "=== Full setup complete! ==="
echo ""
echo "To use ComfyUI:"
echo "1. conda activate comfy-env"
echo "2. comfy --help"
echo ""
echo "Models are available in: ~/comfy/ComfyUI/models/"