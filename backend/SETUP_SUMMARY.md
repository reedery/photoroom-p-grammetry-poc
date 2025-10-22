# Local 3D Model Generation Server - Setup Summary

## What's Been Done ✅

All Modal-related code has been removed and replaced with a local server setup. Here's what's been completed:

### 1. Created Local FastAPI Server (`app.py`)
- ✅ Removed all Modal dependencies
- ✅ Pure FastAPI/uvicorn implementation
- ✅ CORS enabled for frontend communication
- ✅ CUDA detection and GPU information
- ✅ Multiple endpoints for health checks, generation, and demo

### 2. Updated TripoSR Pipeline (`triposr_pipeline.py`)
- ✅ Flexible path detection for local environments
- ✅ Supports multiple installation locations:
  - `backend/TripoSR/` (local)
  - `~/TripoSR` (home directory)
  - `/root/TripoSR` (container/original)
  - Custom via `TRIPOSR_DIR` environment variable

### 3. Cloned TripoSR Repository
- ✅ TripoSR cloned to `backend/TripoSR/`
- ✅ Ready for installation

### 4. Created Installation Scripts
- ✅ `setup.sh` - Interactive setup with virtual environment creation
- ✅ `install.sh` - Streamlined installation once pip is available
- ✅ `run_server.sh` - Easy server startup script

### 5. Created Requirements File
- ✅ `requirements.txt` - All dependencies for local setup
  - FastAPI and uvicorn
  - PyTorch with CUDA 12.1 support
  - ONNX Runtime GPU
  - Image processing libraries
  - All TripoSR dependencies

### 6. Created Documentation
- ✅ `README.md` - Complete setup guide
- ✅ `INSTALL_INSTRUCTIONS.md` - Step-by-step installation
- ✅ `SETUP_SUMMARY.md` - This file

## System Information

- **OS**: Linux (WSL2)
- **Python**: 3.12.3
- **GPU**: NVIDIA GeForce RTX 4060 (8GB VRAM)
- **CUDA Driver**: 12.3
- **TripoSR**: Cloned and ready

## What You Need to Do Now

### Step 1: Install pip (Required)

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
```

### Step 2: Run Installation Script

```bash
cd /home/ryanreede/projects/photoroom-p-grammetry-poc/backend
./install.sh
```

This will:
1. Create a virtual environment
2. Install PyTorch with CUDA support
3. Install ONNX Runtime GPU
4. Install TripoSR requirements
5. Install server dependencies
6. Verify CUDA setup
7. Create `.env` file

### Step 3: Install System Dependencies (Optional but Recommended)

For OpenGL rendering (texture baking):

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

### Step 4: Configure API Key (Optional)

If you want background removal, edit `.env`:

```bash
nano .env
# Change: PHOTOROOM_API_KEY=your_actual_api_key_here
```

### Step 5: Start the Server

```bash
# Make sure virtual environment is active
source venv/bin/activate

# Start server
python3 app.py
```

Or use the run script:

```bash
./run_server.sh
```

## Server Endpoints

Once running on `http://localhost:8000`:

### Health Check
```bash
curl http://localhost:8000/health
```

### Generate 3D Model
```bash
curl -X POST http://localhost:8000/generate \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "photoroom_api_key=your_key"
```

### Run Demo
```bash
curl http://localhost:8000/demo
```

## Architecture Changes

### Before (Modal)
```
User → Modal Web Endpoint → Modal GPU Function → TripoSR
```

### After (Local)
```
User/Frontend → Local FastAPI Server → TripoSR (Local CUDA)
```

## Key Differences from Modal Setup

| Feature | Modal | Local |
|---------|-------|-------|
| **Deployment** | Cloud-based | Local machine |
| **GPU** | L40S (48GB) | RTX 4060 (8GB) |
| **Scaling** | Automatic | Manual |
| **Startup** | ~30-90s cold start | Instant after first run |
| **Cost** | Pay per use | Free (your hardware) |
| **API Keys** | Modal secrets | Environment variables |
| **File Storage** | Modal volumes | Local filesystem |
| **Concurrency** | Up to 4 simultaneous | Limited by GPU |

## File Structure

```
backend/
├── app.py                   # ✅ LOCAL: FastAPI server (Modal removed)
├── triposr_pipeline.py      # ✅ UPDATED: Local path support
├── background_removal.py    # UNCHANGED
├── requirements.txt         # ✅ LOCAL: Local dependencies
├── setup.sh                 # ✅ NEW: Interactive setup
├── install.sh               # ✅ NEW: Streamlined install
├── run_server.sh            # ✅ NEW: Server startup
├── README.md                # ✅ NEW: Complete documentation
├── INSTALL_INSTRUCTIONS.md  # ✅ NEW: Step-by-step guide
├── SETUP_SUMMARY.md         # ✅ NEW: This file
├── .env                     # Will be created by install.sh
└── TripoSR/                 # ✅ CLONED: Ready to install
```

## Expected Performance

With your RTX 4060 (8GB VRAM):

- **First request**: 30-60 seconds (model loading)
- **Subsequent requests**: 5-15 seconds per image set
- **Concurrent requests**: 1-2 recommended (8GB VRAM limit)
- **Max images per request**: 5 (as designed)

## Troubleshooting

### CUDA Not Available After Install

```bash
# Activate venv
source venv/bin/activate

# Test
python3 -c "import torch; print(torch.cuda.is_available())"
```

If False:
1. Check nvidia-smi works
2. Reinstall PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cu121`
3. WSL2 may need Windows NVIDIA driver update

### Out of Memory

With 8GB VRAM:
- Process one image set at a time
- Close other GPU applications
- Restart server between large jobs

### Module Not Found Errors

```bash
source venv/bin/activate
pip install -r requirements.txt
pip install -r TripoSR/requirements.txt
```

## Next Steps After Server is Running

1. **Test locally** with curl or Postman
2. **Update frontend** to point to `http://localhost:8000`
3. **Consider deployment**:
   - Use systemd service for auto-start
   - Add nginx reverse proxy
   - Set up HTTPS with Let's Encrypt
   - Configure firewall rules

## Frontend Integration

Update your frontend to use the local server:

```javascript
// Change from Modal endpoint to local
const API_URL = 'http://localhost:8000';

// Upload images
const formData = new FormData();
formData.append('files', file1);
formData.append('files', file2);

const response = await fetch(`${API_URL}/generate`, {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

## Questions?

Refer to:
- `README.md` - Complete documentation
- `INSTALL_INSTRUCTIONS.md` - Detailed installation steps
- TripoSR repo: https://github.com/VAST-AI-Research/TripoSR

## Summary

✅ All Modal code removed
✅ Local server created and configured
✅ TripoSR cloned and ready
✅ Installation scripts prepared
✅ Documentation complete

🔄 **Next**: Install pip and run `./install.sh`

The server is ready to run on your local machine with CUDA acceleration!

