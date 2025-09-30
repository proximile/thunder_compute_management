#!/bin/bash
set -e

echo "=== Installing Cloudflared ==="

# Update package list
echo "Updating package list..."
sudo apt update

# Download cloudflared .deb package
echo "Downloading cloudflared package..."
cd /tmp
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install the package
echo "Installing cloudflared..."
sudo dpkg -i cloudflared-linux-amd64.deb

# Fix any dependency issues
echo "Fixing any dependency issues..."
sudo apt-get install -f -y

# Clean up
echo "Cleaning up download..."
rm cloudflared-linux-amd64.deb

# Verify installation
echo "Verifying cloudflared installation..."
cloudflared --version

echo "=== Cloudflared installation complete ==="
echo "You can now create tunnels with: cloudflared tunnel --url http://localhost:PORT"