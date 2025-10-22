#!/bin/bash

# Install CUDA Toolkit on WSL2
# This script installs CUDA 12.1 development toolkit

set -e

echo "=========================================="
echo "CUDA Toolkit Installation for WSL2"
echo "=========================================="
echo ""

# Check if running on WSL
if ! grep -qi microsoft /proc/version; then
    echo "This script is designed for WSL2"
    echo "For native Linux, please install CUDA from NVIDIA's website"
    exit 1
fi

echo "Installing CUDA 12.1 toolkit..."
echo ""

# Add NVIDIA package repository
echo "Adding NVIDIA repository..."
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
rm cuda-keyring_1.1-1_all.deb

# Update package list
sudo apt-get update

# Install CUDA toolkit core components (without optional tools that cause dependency issues)
echo ""
echo "Installing CUDA toolkit components..."
echo "This may take 5-10 minutes..."
echo ""

# Install core CUDA toolkit components only (skip nsight-systems which has dependency issues)
sudo apt-get install -y \
    cuda-compiler-12-1 \
    cuda-libraries-dev-12-1 \
    cuda-cudart-dev-12-1 \
    cuda-nvcc-12-1 \
    cuda-nvtx-12-1 \
    libcublas-dev-12-1 \
    libcufft-dev-12-1 \
    libcurand-dev-12-1 \
    libcusolver-dev-12-1 \
    libcusparse-dev-12-1 \
    cuda-driver-dev-12-1

# Create symlink for cuda
if [ ! -L /usr/local/cuda ]; then
    sudo ln -sf /usr/local/cuda-12.1 /usr/local/cuda
fi

echo ""
echo "=========================================="
echo "CUDA Toolkit Installation Complete!"
echo "=========================================="
echo ""
echo "CUDA has been installed to: /usr/local/cuda-12.1"
echo "Symlink created at: /usr/local/cuda"
echo ""
echo "Verifying installation..."
if [ -f "/usr/local/cuda/bin/nvcc" ]; then
    /usr/local/cuda/bin/nvcc --version
    echo ""
    echo "✓ CUDA compiler (nvcc) is working!"
else
    echo "⚠ Warning: nvcc not found. Installation may be incomplete."
fi
echo ""
echo "Next steps:"
echo "  1. Close this terminal and open a new one, OR"
echo "  2. Run: source ~/.bashrc"
echo "  3. Re-run the installation: ./install.sh"
echo ""

# Add to .bashrc if not already there
if ! grep -q "CUDA_HOME" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# CUDA environment" >> ~/.bashrc
    echo "export CUDA_HOME=/usr/local/cuda-12.1" >> ~/.bashrc
    echo "export PATH=\$PATH:\$CUDA_HOME/bin" >> ~/.bashrc
    echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:\$CUDA_HOME/lib64:/usr/lib/wsl/lib" >> ~/.bashrc
    echo ""
    echo "✓ Added CUDA paths to ~/.bashrc"
fi

echo ""
echo "Environment variables have been set up."
echo "Reload your shell or run: source ~/.bashrc"
echo ""

