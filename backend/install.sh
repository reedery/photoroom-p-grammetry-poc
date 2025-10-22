#!/bin/bash

# Complete installation script for local 3D model generation server
# Run this AFTER installing pip: sudo apt install python3-pip python3-venv

set -e  # Exit on error

echo "=========================================="
echo "3D Model Generation - Complete Installation"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Check pip
echo -e "${YELLOW}[1/8] Checking pip installation...${NC}"
if ! python3 -m pip --version &> /dev/null; then
    echo -e "${RED}✗ pip not found. Please install it first:${NC}"
    echo "  sudo apt update"
    echo "  sudo apt install -y python3-pip python3-venv"
    exit 1
fi
echo -e "${GREEN}✓ pip found${NC}"
echo ""

# Step 2: Create virtual environment
echo -e "${YELLOW}[2/8] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Step 3: Upgrade pip
echo -e "${YELLOW}[3/8] Upgrading pip...${NC}"
pip install --upgrade pip
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Step 4: Install PyTorch with CUDA
echo -e "${YELLOW}[4/8] Installing PyTorch with CUDA 12.1 support...${NC}"
echo "This may take several minutes..."
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
echo -e "${GREEN}✓ PyTorch installed${NC}"
echo ""

# Step 5: Install ONNX Runtime GPU
echo -e "${YELLOW}[5/8] Installing ONNX Runtime GPU...${NC}"
pip install onnxruntime-gpu==1.20.1
echo -e "${GREEN}✓ ONNX Runtime GPU installed${NC}"
echo ""

# Step 6: Install TripoSR requirements
echo -e "${YELLOW}[6/8] Installing TripoSR requirements...${NC}"
if [ -f "TripoSR/requirements.txt" ]; then
    # Check GCC version (CUDA 12.1 requires GCC <= 12)
    GCC_VERSION=$(gcc -dumpversion | cut -d. -f1)
    echo "Detected GCC version: $(gcc --version | head -n1)"
    
    if [ "$GCC_VERSION" -gt 12 ]; then
        echo -e "${YELLOW}⚠ Warning: GCC $GCC_VERSION detected${NC}"
        echo "  CUDA 12.1 requires GCC 12 or earlier"
        echo ""
        
        # Check if GCC 12 is available
        if command -v gcc-12 &> /dev/null; then
            echo "✓ GCC 12 is available, using it for compilation"
            export CC=gcc-12
            export CXX=g++-12
        else
            echo "GCC 12 not found. Installing it..."
            echo ""
            echo "To install GCC 12:"
            echo "  ./install_gcc12.sh"
            echo ""
            read -p "Install GCC 12 now? (y/n) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ./install_gcc12.sh
                export CC=gcc-12
                export CXX=g++-12
            else
                echo "Trying with current GCC (may fail)..."
                export CC=gcc
                export CXX=g++
            fi
        fi
    else
        echo "✓ GCC version is compatible"
        export CC=gcc
        export CXX=g++
    fi
    
    # Find CUDA installation
    CUDA_FOUND=0
    for cuda_dir in /usr/local/cuda-12.1 /usr/local/cuda-12.3 /usr/local/cuda /usr/local/cuda-12 /opt/cuda; do
        if [ -d "$cuda_dir" ]; then
            export CUDA_HOME=$cuda_dir
            export PATH=$PATH:$cuda_dir/bin
            export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$cuda_dir/lib64:/usr/lib/wsl/lib
            export CUDA_TOOLKIT_ROOT_DIR=$cuda_dir
            echo "Found CUDA at: $cuda_dir"
            CUDA_FOUND=1
            break
        fi
    done
    
    if [ $CUDA_FOUND -eq 0 ]; then
        echo -e "${YELLOW}⚠ Warning: CUDA toolkit not found${NC}"
        echo "  torchmcubes compilation may fail"
        echo ""
        echo "To install CUDA toolkit:"
        echo "  ./install_cuda_toolkit.sh"
        echo ""
        echo "Or see: CUDA_SETUP.md"
        echo ""
        echo "Trying to continue anyway..."
        sleep 2
    fi
    
    # Install TripoSR requirements
    pip install -r TripoSR/requirements.txt --no-cache-dir
    
    # Check if installation succeeded
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠ TripoSR requirements installation had issues${NC}"
        echo ""
        echo "If torchmcubes failed to build, you have two options:"
        echo ""
        echo "Option 1: Install CUDA toolkit and retry (Recommended)"
        echo "  ./install_cuda_toolkit.sh"
        echo "  source ~/.bashrc"
        echo "  pip install -r TripoSR/requirements.txt --no-cache-dir"
        echo ""
        echo "Option 2: Continue without torchmcubes"
        echo "  (The server will still work, but mesh quality may be affected)"
        echo ""
        echo "See CUDA_SETUP.md for detailed instructions"
        echo ""
        read -p "Continue with installation anyway? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✓ TripoSR requirements installed${NC}"
    fi
else
    echo -e "${RED}✗ TripoSR/requirements.txt not found${NC}"
    echo "  Run ./setup.sh first to clone TripoSR"
    exit 1
fi
echo ""

# Step 7: Install server requirements
echo -e "${YELLOW}[7/8] Installing server requirements...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Server requirements installed${NC}"
echo ""

# Step 8: Verify CUDA setup
echo -e "${YELLOW}[8/8] Verifying CUDA setup...${NC}"
python3 << 'PYEOF'
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
else:
    print("⚠ WARNING: CUDA not available")
PYEOF
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << 'ENVEOF'
# API Keys
PHOTOROOM_API_KEY=your_photoroom_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000

# TripoSR Configuration (optional)
# TRIPOSR_DIR=/path/to/TripoSR
ENVEOF
    echo -e "${GREEN}✓ .env file created${NC}"
    echo "  Please edit .env and add your Photoroom API key if needed"
    echo ""
fi

# System dependencies check
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo -e "${YELLOW}System Dependencies Check${NC}"
    echo "The following packages are needed for OpenGL rendering:"
    echo "  libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 xvfb"
    echo ""
    echo "Install them with:"
    echo "  sudo apt-get install -y libgl1-mesa-glx libgl1-mesa-dri libglib2.0-0 libsm6 libxrender1 libxext6 xvfb"
    echo ""
fi

echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo ""
echo "To start the server:"
echo ""
echo "  1. Make sure virtual environment is active:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Start the server:"
echo "     python3 app_local.py"
echo ""
echo "  Or use the run script:"
echo "     ./run_server.sh"
echo ""
echo "API will be available at: http://localhost:8000"
echo ""
echo "Endpoints:"
echo "  GET  /health   - Check server status"
echo "  POST /generate - Generate 3D model"
echo "  GET  /demo     - Run demo"
echo ""

