#!/bin/bash

# Setup script for local 3D model generation server
# This script installs TripoSR, PyTorch with CUDA, and all dependencies

set -e  # Exit on error

echo "=========================================="
echo "3D Model Generation Server Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"
echo ""

# Check for Python
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.11 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Check for CUDA
echo -e "${YELLOW}Checking CUDA installation...${NC}"
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $5}' | sed 's/,//')
    echo -e "${GREEN}✓ CUDA $CUDA_VERSION found${NC}"
else
    echo -e "${YELLOW}⚠ CUDA not found in PATH. GPU acceleration may not work.${NC}"
    echo "  Please ensure CUDA 12.1+ is installed if you want GPU support."
fi
echo ""

# Check for virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠ Not running in a virtual environment${NC}"
    echo "  It's recommended to use a virtual environment."
    echo ""
    read -p "Create and activate a virtual environment? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo "Activating virtual environment..."
        source venv/bin/activate
        echo -e "${GREEN}✓ Virtual environment created and activated${NC}"
        echo ""
    fi
else
    echo -e "${GREEN}✓ Running in virtual environment: $VIRTUAL_ENV${NC}"
    echo ""
fi

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
python3 -m pip install --upgrade pip
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Install PyTorch with CUDA support
echo -e "${YELLOW}Installing PyTorch with CUDA 12.1 support...${NC}"
echo "This may take a few minutes..."
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
echo -e "${GREEN}✓ PyTorch installed${NC}"
echo ""

# Install ONNX Runtime GPU
echo -e "${YELLOW}Installing ONNX Runtime GPU...${NC}"
pip install onnxruntime-gpu==1.20.1
echo -e "${GREEN}✓ ONNX Runtime GPU installed${NC}"
echo ""

# Clone TripoSR repository
echo -e "${YELLOW}Setting up TripoSR...${NC}"
if [ -d "TripoSR" ]; then
    echo "TripoSR directory already exists. Skipping clone."
else
    echo "Cloning TripoSR repository..."
    git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git
    echo -e "${GREEN}✓ TripoSR cloned${NC}"
fi
echo ""

# Install TripoSR requirements
echo -e "${YELLOW}Installing TripoSR requirements...${NC}"
if [ -f "TripoSR/requirements.txt" ]; then
    # Set environment variables for compilation
    export CXX=g++
    if [ -d "/usr/local/cuda" ]; then
        export CUDA_HOME=/usr/local/cuda
        export PATH=$PATH:/usr/local/cuda/bin
        export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64
    fi
    
    # Install TripoSR requirements
    pip install -r TripoSR/requirements.txt --no-cache-dir
    echo -e "${GREEN}✓ TripoSR requirements installed${NC}"
else
    echo -e "${RED}✗ TripoSR requirements.txt not found${NC}"
fi
echo ""

# Install additional dependencies
echo -e "${YELLOW}Installing additional dependencies...${NC}"
pip install imageio==2.36.1 omegaconf==2.3.0
echo -e "${GREEN}✓ Additional dependencies installed${NC}"
echo ""

# Install server requirements
echo -e "${YELLOW}Installing server requirements...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Server requirements installed${NC}"
else
    echo -e "${RED}✗ requirements.txt not found${NC}"
fi
echo ""

# Install system dependencies for OpenGL/Mesa (if on Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${YELLOW}Checking system dependencies...${NC}"
    echo "The following packages are needed for OpenGL rendering:"
    echo "  - libgl1-mesa-glx, libglib2.0-0, libsm6, libxrender1, libxext6, xvfb"
    echo ""
    
    if command -v apt-get &> /dev/null; then
        read -p "Install system dependencies via apt? (requires sudo) (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt-get update
            sudo apt-get install -y \
                libgl1-mesa-glx \
                libgl1-mesa-dri \
                libglib2.0-0 \
                libsm6 \
                libxrender1 \
                libxext6 \
                xvfb
            echo -e "${GREEN}✓ System dependencies installed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ apt-get not found. Please manually install the packages above.${NC}"
    fi
    echo ""
fi

# Verify PyTorch CUDA
echo -e "${YELLOW}Verifying PyTorch CUDA setup...${NC}"
python3 << EOF
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
else:
    print("⚠ WARNING: CUDA is not available. GPU acceleration will not work.")
    print("  Make sure NVIDIA drivers and CUDA toolkit are properly installed.")
EOF
echo ""

# Create .env template if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env template...${NC}"
    cat > .env << 'ENVEOF'
# API Keys
PHOTOROOM_API_KEY=your_photoroom_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000

# TripoSR Configuration (optional)
# TRIPOSR_DIR=/path/to/TripoSR
ENVEOF
    echo -e "${GREEN}✓ .env template created${NC}"
    echo "  Please edit .env and add your Photoroom API key if needed."
    echo ""
fi

echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "To start the server:"
echo "  1. Activate virtual environment (if not already active):"
echo "     source venv/bin/activate"
echo ""
echo "  2. Set environment variables (optional):"
echo "     export PHOTOROOM_API_KEY=your_key_here"
echo ""
echo "  3. Start the server:"
echo "     python3 app.py"
echo ""
echo "  Or use uvicorn directly:"
echo "     uvicorn app:app --host 0.0.0.0 --port 8000"
echo ""
echo "API Endpoints:"
echo "  - GET  /         - Health check"
echo "  - GET  /health   - Detailed health check"
echo "  - POST /generate - Generate 3D model from images"
echo "  - GET  /demo     - Run demo with sample images"
echo ""

