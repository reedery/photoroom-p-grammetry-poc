# Photogrammetry POC

Full-stack application for creating 3D models from multiple images using photogrammetry.

## Project Structure

- **Backend**: Modal-based Python backend for processing images
- **Frontend**: Modern HTML/CSS/JS web interface with Three.js 3D viewer

## Pipeline Status

- [x] Images uploaded
- [x] Frontend image uploader with multiple file support
- [x] Frontend 3D viewer (Three.js)
- [ ] Images resized (locally)
- [x] Images aligned with SFM
- [x] Images BG removed (Photoroom API integration)
- [ ] Images merged to form 3D model via photogrammetry
- [ ] Display final 3D model in frontend viewer

## Backend Setup

### Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r backend/requirements.txt
```

### Deploy to Modal

```bash
modal deploy backend/app.py
```

## Running the Application

### Backend (Modal Commands)

**Development mode (auto-reload):**

```bash
modal serve backend/app.py
```

**Test locally:**

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

Upload images for processing.

**Request:**

- `files`: Multiple image files
- `photoroom_api_key`: Optional API key

**Response:**

```json
{
  "status": "success",
  "files_received": 2,
  "file_info": [...],
  "api_key_present": true,
  "pipeline_result": {
    "images_saved": 2,
    "work_directory": "/tmp/reconstruction",
    "image_directory": "/tmp/reconstruction/images",
    "output_directory": "/tmp/reconstruction/output"
  }
}
```

### Test with curl

```bash
curl -X POST https://[your-url].modal.run \
  -F "files=@image1.png" \
  -F "files=@image2.png" \
  -F "photoroom_api_key=your_key"
```

## Backend Functions

- `process_images`: Modal function that processes uploaded images
- `web_app`: FastAPI ASGI app serving the upload endpoint
- `test`: Local entrypoint for testing with images from `img_testing/`

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

- Python 3.9+
- Modal (serverless deployment)
- FastAPI (web framework)
- COLMAP (structure from motion)

**Frontend:**

- HTML5, CSS3, JavaScript (ES6+)
- Three.js (3D visualization)
- OrbitControls (camera interaction)
- LocalStorage API (persistent data)
