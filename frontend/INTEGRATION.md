# Frontend-Backend Integration Guide

## 🎉 Integration Complete!

Both frontend and backend servers are running and fully integrated!

**Frontend:** http://localhost:8080  
**Backend API:** http://localhost:8000  
**Backend Health:** http://localhost:8000/health

## Overview
The frontend sends single images to the backend for 3D model generation and renders the results using Three.js.

## Frontend Features Implemented

### 1. Single Image Input
- ✅ User can upload one image via file input
- ✅ Demo buttons load `mug.jpg` or `shoe.jpg` from the `img/` folder
- ✅ Image preview displays before processing

### 2. Loading Indicator
- ✅ Animated spinner shows during processing
- ✅ Button disabled state while processing
- ✅ Status messages inform user of progress

### 3. 3D Model Rendering
- ✅ Three.js viewer with orbit controls
- ✅ Support for PLY and OBJ format loading
- ✅ Auto-centering and scaling of models
- ✅ Proper lighting and camera setup
- ✅ Auto-rotate enabled after model loads

## ✅ Backend Integration (COMPLETED)

### API Endpoint

**Endpoint:** `POST http://localhost:8000/process` ✅ IMPLEMENTED

**Request Format:** `multipart/form-data`

**Request Fields:**
```
- image: File (the uploaded image)
- photoroom_api_key: String (user's Photoroom API key)
```

### Backend Response Format

The backend returns a JSON response in the following formats:

#### Success Response
```json
{
  "success": true,
  "model_url": "http://localhost:8000/models/output_model.obj",
  "format": "obj",
  "message": "Model generated successfully"
}
```

#### Error Response
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

### Additional Backend Endpoints

- `GET /` - Health check endpoint
- `GET /health` - Detailed health and CUDA status
- `POST /generate` - Multi-image generation endpoint
- `GET /models/{filename}` - Serve generated 3D models ✅
- `GET /download/{filename}` - Download generated files
- `GET /demo` - Run demo with pre-loaded images

### Supported Model Formats
- **PLY** (recommended) - Point cloud and mesh format
- **OBJ** - Mesh format

The frontend will determine which loader to use based on the `format` field in the response.

## Frontend Code Structure

### Key Functions

#### `processImage()`
Located in `app.js` (lines 328-379)
- Sends image to backend
- Handles loading state
- Processes response
- Calls `load3DModel()` with result

#### `load3DModel(modelUrl, format)`
Located in `app.js` (lines 102-202)
- Loads PLY or OBJ files
- Centers and scales model
- Replaces placeholder cube
- Enables auto-rotation

### State Management
```javascript
let selectedFile = null;  // Currently selected image file
let apiKey = '';          // Photoroom API key
let currentModel = null;  // Current 3D model in scene
```

## ✅ Testing the Integration (SERVERS RUNNING)

### How to Use the Application

1. **Access the Frontend:**
   - Open your browser and go to http://localhost:8080

2. **Enter Your Photoroom API Key:**
   - Enter your Photoroom API key in the input field
   - The key will be saved in local storage for future use

3. **Select an Image:**
   - Click "Select Image" to upload your own image, OR
   - Click "👟 Try a Shoe" or "☕ Try a Mug" to use demo images

4. **Generate 3D Model:**
   - Click "Generate 3D Model" button
   - The backend will:
     - Remove the background using Photoroom API
     - Generate a 3D model using TripoSR
     - Return the model file

5. **View the Result:**
   - The 3D model will automatically load in the viewer
   - Use your mouse to rotate and zoom the model
   - The model will auto-rotate for better visualization

### Server Status

**Backend Server:**
- Status: ✅ RUNNING
- Port: 8000
- CUDA: Enabled (NVIDIA GeForce RTX 4060 Laptop GPU)
- Python environment: `/home/ryanreede/projects/photoroom-p-grammetry-poc/backend/venv`

**Frontend Server:**
- Status: ✅ RUNNING
- Port: 8080
- Type: Python HTTP server

### To Restart the Servers:

**Backend:**
```bash
cd /home/ryanreede/projects/photoroom-p-grammetry-poc/backend
source venv/bin/activate
python app.py
```

**Frontend:**
```bash
cd /home/ryanreede/projects/photoroom-p-grammetry-poc/frontend
python3 -m http.server 8080
```

## ✅ Backend Implementation Details

### Workflow (IMPLEMENTED)
1. ✅ Accept single image upload via `/process` endpoint
2. ✅ Remove background using Photoroom API (optional)
3. ✅ Run TripoSR for 3D reconstruction (GPU-accelerated)
4. ✅ Generate OBJ file with mesh
5. ✅ Save to `/tmp/reconstruction/` directory
6. ✅ Return model URL in JSON response

### CORS Configuration ✅
CORS is properly configured in the backend:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### File Serving ✅
Backend serves generated model files via:
```python
@app.get("/models/{filename}")
async def serve_model(filename: str):
    # Serves OBJ, PLY, MTL files from triposr_output directories
    return FileResponse(path=file_path, media_type="model/obj")
```

## Error Handling

The frontend handles the following error scenarios:
- ✅ No image selected
- ✅ No API key provided
- ✅ Network errors
- ✅ Backend errors (non-200 status)
- ✅ Model loading errors

## Future Enhancements

Potential improvements to consider:
- [ ] WebSocket connection for real-time progress updates
- [ ] Job queue system for long-running processes
- [ ] Model caching to avoid regeneration
- [ ] Texture support for more realistic rendering
- [ ] Export functionality (download model)
- [ ] Multiple camera angles/views
- [ ] Quality settings (low/medium/high poly)

## ✅ Actual Backend Response Flow (IMPLEMENTED)

```
1. Frontend sends image via POST /process
   ↓
2. Backend receives and validates (FastAPI)
   ↓
3. Background removal (Photoroom API with rembg GPU fallback)
   ↓
4. 3D reconstruction (TripoSR with CUDA acceleration)
   ↓
5. Model generation (OBJ format with mesh)
   ↓
6. Save to /tmp/reconstruction/request_*/triposr_output/
   ↓
7. Return JSON: {"success": true, "model_url": "http://localhost:8000/models/mesh.obj", "format": "obj"}
   ↓
8. Frontend loads via GET /models/{filename}
   ↓
9. Three.js renders and displays model with auto-rotate
```

### Example API Interaction

**Request:**
```bash
curl -X POST http://localhost:8000/process \
  -F "image=@shoe.jpg" \
  -F "photoroom_api_key=your_api_key_here"
```

**Response:**
```json
{
  "success": true,
  "model_url": "http://localhost:8000/models/mesh.obj",
  "format": "obj",
  "message": "Model generated successfully"
}
```

**Then Frontend Loads:**
```javascript
load3DModel("http://localhost:8000/models/mesh.obj", "obj");
```

## Contact

If you need any changes to the frontend integration or have questions about the expected formats, update this file or modify the frontend code as needed.

