#!/bin/bash
set -e

echo "=== Installing Miniforge ==="

# Remove any existing miniconda3 installation
if [ -d "$HOME/miniconda3" ]; then
    echo "Removing existing miniconda3 installation..."
    rm -rf "$HOME/miniconda3"
fi

# Remove any existing miniforge3 installation
if [ -d "$HOME/miniforge3" ]; then
    echo "Removing existing miniforge3 installation..."
    rm -rf "$HOME/miniforge3"
fi

# Download Miniforge installer
echo "Downloading Miniforge installer..."
cd "$HOME"

# Use wget as recommended, with fallback to curl
MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
INSTALLER_NAME="Miniforge3.sh"

echo "Downloading from: $MINIFORGE_URL"
if command -v wget &> /dev/null; then
    echo "Using wget for download..."
    wget -O "$INSTALLER_NAME" "$MINIFORGE_URL"
else
    echo "Using curl for download..."
    curl -fsSL -o "$INSTALLER_NAME" --connect-timeout 30 --max-time 300 --retry 3 "$MINIFORGE_URL"
fi

if [ ! -f "$INSTALLER_NAME" ]; then
    echo "Error: Failed to download Miniforge installer"
    exit 1
fi

echo "Download completed: $(ls -lh $INSTALLER_NAME)"

# Install Miniforge in batch mode with timeout
echo "Installing Miniforge in batch mode..."
echo "Using installation path: $HOME/miniforge3"

# Run installation with timeout to prevent hanging
timeout 300 bash "$INSTALLER_NAME" -b -p "$HOME/miniforge3"
install_exit_code=$?

if [ $install_exit_code -eq 124 ]; then
    echo "Error: Miniforge installation timed out after 5 minutes"
    exit 1
elif [ $install_exit_code -ne 0 ]; then
    echo "Error: Miniforge installation failed with exit code $install_exit_code"
    exit 1
fi

echo "Miniforge installation completed successfully"

# Verify installation
if [ ! -d "$HOME/miniforge3" ]; then
    echo "Error: Miniforge installation failed"
    exit 1
fi

# Clean up installer
echo "Cleaning up installer..."
rm "$INSTALLER_NAME"

# Initialize conda
echo "Initializing conda..."
"$HOME/miniforge3/bin/conda" init bash

echo "=== Miniforge installation complete ==="
echo "Please run 'source ~/.bashrc' or restart your shell to use conda"
echo "Then you can create environments with: conda create -n myenv python=3.11"