# Local 3D Model Generation Server

This is a local FastAPI server that runs TripoSR with CUDA acceleration to generate 3D models from images. This replaces the Modal cloud setup with a local server running on your machine.

## Prerequisites

- **Python 3.11+**
- **CUDA 12.1+** and compatible NVIDIA GPU (recommended for good performance)
- **Ubuntu/Debian Linux** (or WSL2 on Windows)
- **8GB+ GPU VRAM** (16GB+ recommended for best results)

## Quick Start

### 1. Run Setup Script

The setup script will install all dependencies, clone TripoSR, and configure the environment:

```bash
cd backend
./setup.sh
```

This will:
- Check Python and CUDA installation
- Optionally create a virtual environment
- Install PyTorch with CUDA 12.1 support
- Clone and set up TripoSR repository
- Install all required dependencies
- Install system packages for OpenGL rendering

### 2. Configure Environment (Optional)

Edit the `.env` file to add your Photoroom API key if you want background removal:

```bash
PHOTOROOM_API_KEY=your_key_here
```

Or set it as an environment variable:

```bash
export PHOTOROOM_API_KEY=your_key_here
```

### 3. Start the Server

```bash
# Activate virtual environment (if created)
source venv/bin/activate

# Start server
python3 app_local.py
```

Or use uvicorn directly:

```bash
uvicorn app_local:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

## API Endpoints

### Health Check
```bash
GET /
GET /health
```

Returns server status and CUDA information.

**Example:**
```bash
curl http://localhost:8000/health
```

### Generate 3D Model
```bash
POST /generate
```

Upload images and generate a 3D model.

**Parameters:**
- `files`: List of image files (up to 5) - multipart/form-data
- `photoroom_api_key`: Optional Photoroom API key for background removal - form field
- `include_files`: Whether to include base64-encoded output files in response - form field (default: false)

**Example:**
```bash
curl -X POST http://localhost:8000/generate \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "photoroom_api_key=your_key_here"
```

**With Python:**
```python
import requests

files = [
    ('files', open('image1.jpg', 'rb')),
    ('files', open('image2.jpg', 'rb')),
]

response = requests.post(
    'http://localhost:8000/generate',
    files=files,
    data={'photoroom_api_key': 'your_key_here'}
)

print(response.json())
```

### Run Demo
```bash
GET /demo
```

Runs a demo with images from the `img/` directory.

**Example:**
```bash
curl http://localhost:8000/demo
```

### Download File
```bash
GET /download/{filename}
```

Download a generated output file.

**Example:**
```bash
curl -O http://localhost:8000/download/mesh.obj
```

## Project Structure

```
backend/
├── app_local.py              # Local FastAPI server (replaces Modal)
├── triposr_pipeline.py       # TripoSR processing pipeline
├── background_removal.py     # Photoroom API background removal
├── requirements_local.txt    # Python dependencies for local setup
├── requirements.txt          # Original dependencies (kept for reference)
├── setup.sh                  # Automated setup script
├── .env                      # Environment variables (created by setup.sh)
├── TripoSR/                  # TripoSR repository (cloned by setup.sh)
└── img/                      # Sample images for demo
```

## Manual Installation

If you prefer to install manually instead of using the setup script:

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install PyTorch with CUDA

```bash
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
```

### 3. Install ONNX Runtime GPU

```bash
pip install onnxruntime-gpu==1.20.1
```

### 4. Clone TripoSR

```bash
git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git
```

### 5. Install TripoSR Requirements

```bash
export CXX=g++
export CUDA_HOME=/usr/local/cuda
export PATH=$PATH:/usr/local/cuda/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64

pip install -r TripoSR/requirements.txt --no-cache-dir
pip install imageio==2.36.1 omegaconf==2.3.0
```

### 6. Install Server Requirements

```bash
pip install -r requirements_local.txt
```

### 7. Install System Dependencies (Linux)

```bash
sudo apt-get update
sudo apt-get install -y \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    xvfb
```

## Troubleshooting

### CUDA Not Available

If PyTorch can't detect CUDA:

1. Check NVIDIA driver installation:
   ```bash
   nvidia-smi
   ```

2. Check CUDA toolkit installation:
   ```bash
   nvcc --version
   ```

3. Verify PyTorch CUDA:
   ```python
   import torch
   print(torch.cuda.is_available())
   print(torch.cuda.get_device_name(0))
   ```

4. Reinstall PyTorch with correct CUDA version:
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

### ModuleNotFoundError

If you get import errors, make sure all dependencies are installed:

```bash
pip install -r requirements_local.txt
pip install -r TripoSR/requirements.txt
```

### OpenGL/Display Errors

The server uses Xvfb for headless OpenGL rendering. If you get display errors:

1. Make sure Xvfb is installed:
   ```bash
   sudo apt-get install xvfb
   ```

2. Check if Xvfb can start:
   ```bash
   Xvfb :99 -screen 0 1024x768x24 &
   export DISPLAY=:99
   ```

### Out of Memory Errors

If you run out of GPU memory:

1. Use a smaller batch size
2. Close other GPU applications
3. Use a GPU with more VRAM (16GB+ recommended)

## Performance Notes

- **First request**: Slower due to model loading (~30-60 seconds)
- **Subsequent requests**: Much faster (~5-15 seconds per image set)
- **GPU required**: The model needs a CUDA-capable GPU for reasonable performance
- **CPU fallback**: Will work on CPU but will be very slow (minutes per image)

## Differences from Modal Version

The local version differs from the Modal cloud version in several ways:

1. **No Modal dependencies** - Pure FastAPI/uvicorn server
2. **Local file system** - Uses `/tmp/reconstruction` instead of Modal volumes
3. **Environment variables** - Uses `.env` file or environment variables instead of Modal secrets
4. **Direct execution** - No remote function calls, everything runs locally
5. **Flexible TripoSR location** - Auto-detects TripoSR in multiple locations
6. **Standard CORS** - Configured for web frontend access

## Production Deployment

For production deployment:

1. Use a process manager like systemd or supervisor
2. Configure CORS properly for your frontend domain
3. Set up proper file cleanup for `/tmp/reconstruction`
4. Use nginx or another reverse proxy
5. Set up HTTPS with Let's Encrypt
6. Consider rate limiting and authentication
7. Monitor GPU usage and memory

## License

This project uses TripoSR which is licensed under the MIT License.

