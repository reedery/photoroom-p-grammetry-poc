# Installation Instructions

## Current Status

✅ TripoSR repository cloned successfully
✅ NVIDIA GPU detected: RTX 4060 (8GB VRAM)
✅ CUDA 12.3 driver available
✅ Python 3.12.3 installed

❌ pip not installed - requires sudo access

## Quick Install Steps

### 1. Install pip and venv

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
```

### 2. Create and Activate Virtual Environment (Recommended)

```bash
cd /home/ryanreede/projects/photoroom-p-grammetry-poc/backend
python3 -m venv venv
source venv/bin/activate
```

### 3. Install PyTorch with CUDA 12.1 Support

```bash
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
```

### 4. Install ONNX Runtime GPU

```bash
pip install onnxruntime-gpu==1.20.1
```

### 5. Install TripoSR Requirements

```bash
pip install -r TripoSR/requirements.txt --no-cache-dir
```

### 6. Install Server Requirements

```bash
pip install -r requirements.txt
```

### 7. Install System Dependencies for OpenGL

```bash
sudo apt-get install -y \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    xvfb
```

### 8. Create .env File

```bash
cp .env.example .env
# Edit .env and add your Photoroom API key if needed
nano .env
```

### 9. Start the Server

```bash
# With the virtual environment activated:
python3 app.py
```

Or use the run script:

```bash
./run_server.sh
```

## Alternative: Use the Automated Setup Script

Once pip is installed, you can use the automated setup script:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
cd /home/ryanreede/projects/photoroom-p-grammetry-poc/backend
./setup.sh
```

## Testing CUDA Installation

After installation, verify PyTorch can see your GPU:

```python
python3 << EOF
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
EOF
```

You should see:
- CUDA available: True
- GPU: NVIDIA GeForce RTX 4060
- GPU Memory: ~8.0 GB

## Next Steps After Installation

1. Test the server:
   ```bash
   curl http://localhost:8000/health
   ```

2. Run a demo:
   ```bash
   curl http://localhost:8000/demo
   ```

3. Upload images for 3D generation:
   ```bash
   curl -X POST http://localhost:8000/generate \
     -F "files=@image.jpg"
   ```

## What's Been Set Up

- ✅ Local FastAPI server (`app_local.py`) - replaces Modal
- ✅ TripoSR pipeline with local path detection
- ✅ Setup script for automated installation
- ✅ Run script for easy server startup
- ✅ Comprehensive requirements file
- ✅ Documentation

## Files Created

```
backend/
├── app_local.py              # New local FastAPI server (no Modal)
├── triposr_pipeline.py       # Updated with local path support
├── background_removal.py     # Unchanged
├── requirements_local.txt    # Local dependencies
├── setup.sh                  # Automated setup script
├── run_server.sh            # Server startup script
├── README_LOCAL.md          # Local setup documentation
├── INSTALL_INSTRUCTIONS.md  # This file
└── TripoSR/                 # Cloned TripoSR repository
```

## Troubleshooting

### If CUDA is not detected

Check NVIDIA drivers:
```bash
nvidia-smi
```

If not working, install NVIDIA drivers for WSL2:
```powershell
# From Windows PowerShell (not WSL)
wsl --update
# Download and install NVIDIA drivers for WSL from NVIDIA website
```

### If build dependencies are missing

```bash
sudo apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git
```

### If you get "externally managed environment" error

This is a Python safety feature. Use a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Then retry the pip commands.

