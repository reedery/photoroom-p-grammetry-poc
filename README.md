# 3D Generation POC (TripoSR + Modal GPU)

Full-stack application for generating a 3D model from 1–5 input images using TripoSR on a GPU in Modal. Optionally removes backgrounds via the Photoroom API before reconstruction for cleaner results.

## Project Structure

- **Backend**: Modal-based Python backend for processing images
- **Frontend**: Modern HTML/CSS/JS web interface with Three.js 3D viewer

## Pipeline

- [x] Upload up to 5 images (any common format)
- [x] background removal via Photoroom API (RGBA PNG)
- [x] 3D reconstruction with TripoSR (GPU) on Modal
- [ ] Serve/download the generated mesh to the frontend viewer

## Backend Setup (Modal-only)

You can use Modal directly without a local GPU. A virtualenv is optional for editing and running `modal` CLI.

```bash
pip install modal-client
```

### Deploy to Modal

```bash
export PHOTOROOM_API_KEY=your_key   # optional, enables background removal
modal deploy backend/app.py
```

## Running the Application

### Backend (Modal Commands)

**Development mode (hot-reload server):**

```bash
modal serve backend/app.py
```

**Run the app once (executes on Modal):**

```bash
modal run backend/app.py
```

### Frontend

**Serve the frontend:**

```bash
cd frontend
python3 -m http.server 8080
```

Then open your browser to: `http://localhost:8080`

For more frontend options and details, see [frontend/README.md](frontend/README.md)

## Endpoints

### POST /

Upload 1–5 images for processing.

**Request form fields:**

- `files`: One or more image files (png/jpg/jpeg/webp)
- `photoroom_api_key`: Optional; if provided, backgrounds will be removed via Photoroom prior to 3D generation

**Response (example):**

```json
{
  "status": "success",
  "files_received": 2,
  "file_info": [
    { "filename": "image1.png", "size": 12345, "content_type": "image/png" },
    { "filename": "image2.png", "size": 23456, "content_type": "image/png" }
  ],
  "api_key_present": true,
  "pipeline_result": {
    "success": true,
    "work_directory": "/tmp/reconstruction",
    "image_directory": "/tmp/reconstruction/images",
    "masked_directory": "/tmp/reconstruction/masked",
    "output_directory": "/tmp/reconstruction/triposr_output",
    "background_removal": {
      "processed": 2,
      "failed": 0,
      "total": 2,
      "success": true
    },
    "triposr": {
      "success": true,
      "output_dir": "/tmp/reconstruction/triposr_output",
      "files": [
        "/tmp/reconstruction/triposr_output/model.obj",
        "/tmp/reconstruction/triposr_output/model.mtl",
        "/tmp/reconstruction/triposr_output/texture.png"
      ]
    }
  }
}
```

### Test with curl

```bash
curl -X POST https://[your-url].modal.run \
  -F "files=@image1.png" \
  -F "files=@image2.jpg" \
  -F "photoroom_api_key=$PHOTOROOM_API_KEY"
```

## Backend Functions

- `process_images`: Modal function that masks images (optional) and runs TripoSR on GPU
- `web_app`: FastAPI ASGI app serving the upload endpoint on Modal

## Frontend Features

- ✨ **Multiple Image Upload**: Select and preview multiple images before processing
- 🔑 **API Key Management**: Secure Photoroom API key storage in browser localStorage
- 🎨 **Modern UI**: Beautiful gradient design inspired by Photoroom's aesthetic
- 🎮 **3D Viewer**: Interactive Three.js viewer with orbit controls (currently shows demo cube)
- 📱 **Responsive**: Works on desktop and mobile devices
- 🖼️ **Image Preview Grid**: Review and remove individual images before processing
- 📸 **Photogrammetry Tips**: Built-in guidance on taking proper photos for 3D reconstruction
- 🎯 **Demo Datasets**: Quick-start buttons for shoe and mug examples (coming soon)

## Technologies

**Backend:**

- Python 3.11+
- Modal (serverless, GPU execution)
- FastAPI (web framework)
- TripoSR (single/multi-image 3D reconstruction)
- PyTorch (CUDA 12.1 build)

**Frontend:**

- HTML5, CSS3, JavaScript (ES6+)
- Three.js (3D visualization)
- OrbitControls (camera interaction)
- LocalStorage API (persistent data)
