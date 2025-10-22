#!/bin/bash

# Install GCC 12 for CUDA 12.1 compatibility
# CUDA 12.1 requires GCC 12 or earlier, but Ubuntu 24.04 comes with GCC 13

set -e

echo "=========================================="
echo "Installing GCC 12 for CUDA Compatibility"
echo "=========================================="
echo ""

# Check current GCC version
CURRENT_GCC=$(gcc --version | head -n1)
echo "Current GCC: $CURRENT_GCC"
echo ""

# Install GCC 12 and G++ 12
echo "Installing GCC 12 and G++ 12..."
sudo apt-get update
sudo apt-get install -y gcc-12 g++-12

echo ""
echo "✓ GCC 12 installed"
echo ""

# Set up alternatives so we can switch between GCC versions
echo "Setting up GCC alternatives..."
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 130
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 130
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 120

# Set GCC 12 as default for CUDA compilation
sudo update-alternatives --set gcc /usr/bin/gcc-12
sudo update-alternatives --set g++ /usr/bin/g++-12

echo ""
echo "=========================================="
echo "GCC 12 Installation Complete!"
echo "=========================================="
echo ""

# Verify
GCC_VERSION=$(gcc --version | head -n1)
GPP_VERSION=$(g++ --version | head -n1)

echo "Active GCC: $GCC_VERSION"
echo "Active G++: $GPP_VERSION"
echo ""

if gcc --version | grep -q "gcc (Ubuntu 12"; then
    echo "✓ GCC 12 is now active"
    echo ""
    echo "You can switch back to GCC 13 anytime with:"
    echo "  sudo update-alternatives --set gcc /usr/bin/gcc-13"
    echo "  sudo update-alternatives --set g++ /usr/bin/g++-13"
else
    echo "⚠ Warning: GCC 12 may not be set as default"
    echo "Run: sudo update-alternatives --config gcc"
fi

echo ""
echo "Next step: Re-run installation"
echo "  ./install.sh"
echo ""

