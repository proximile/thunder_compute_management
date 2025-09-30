#!/bin/bash
set -e

echo "=== Setting up ComfyUI Environment ==="

# Ensure conda is available
if [ ! -f "$HOME/miniforge3/bin/conda" ]; then
    echo "Error: Miniforge not found. Please run install_miniforge.sh first."
    exit 1
fi

# Source conda
source "$HOME/miniforge3/etc/profile.d/conda.sh"

# Create comfy environment
echo "Creating comfy-env environment with Python 3.11..."
conda create -n comfy-env python=3.11 -y

# Activate environment
echo "Activating comfy-env environment..."
conda activate comfy-env

# Install comfy CLI
echo "Installing comfy CLI..."
pip install comfy-cli

# Verify installation
echo "Verifying comfy CLI installation..."
comfy --help

# Install ComfyUI with non-interactive flags and GPU specification
echo "Installing ComfyUI..."
comfy --skip-prompt install --nvidia

echo "=== ComfyUI Environment setup complete ==="
echo "Environment 'comfy-env' created with comfy CLI installed"
echo "ComfyUI installed to ~/comfy/ComfyUI"
echo "To use: conda activate comfy-env"