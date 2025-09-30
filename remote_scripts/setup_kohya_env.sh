#!/bin/bash
set -e

echo "Starting Kohya_SS environment setup..."

# Install system dependencies
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3.11 python3.11-venv git wget curl

# Install CUDA 12.8 if not present (check if nvidia-smi works)
if ! command -v nvidia-smi &> /dev/null; then
    echo "Installing CUDA 12.8..."
    # Note: This is a basic CUDA installation
    # Production environments may need more specific CUDA setup
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
    sudo dpkg -i cuda-keyring_1.1-1_all.deb
    sudo apt-get update
    sudo apt-get -y install cuda-toolkit-12-8
else
    echo "CUDA already available"
fi

# Create kohya directory
echo "Setting up Kohya_SS directory..."
cd /home/ubuntu
if [ -d "kohya_ss" ]; then
    echo "Removing existing kohya_ss directory..."
    rm -rf kohya_ss
fi

# Clone kohya_ss repository
echo "Cloning Kohya_SS repository..."
git clone --recursive https://github.com/bmaltais/kohya_ss.git
cd kohya_ss

# Make setup script executable and run it
echo "Running Kohya_SS setup script..."
chmod +x setup.sh
./setup.sh

echo "Kohya_SS environment setup complete!"
echo "Location: /home/ubuntu/kohya_ss"
echo ""
echo "To use Kohya_SS:"
echo "  cd /home/ubuntu/kohya_ss"
echo "  ./gui.sh --listen 0.0.0.0 --server_port 7860 --inbrowser"
echo ""
echo "For tunnel access, use port 7860"