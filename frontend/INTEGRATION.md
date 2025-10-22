# Frontend-Backend Integration Guide

## Overview
The frontend is now prepared to send single images to the backend for 3D model generation and render the results using Three.js.

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

## Backend Integration Requirements

### API Endpoint

**Endpoint:** `POST http://localhost:8000/process`

**Request Format:** `multipart/form-data`

**Request Fields:**
```
- image: File (the uploaded image)
- photoroom_api_key: String (user's Photoroom API key)
```

### Expected Response

The backend should return a JSON response with one of the following formats:

#### Option 1: Direct URL to model file
```json
{
  "success": true,
  "model_url": "http://localhost:8000/models/output_model.ply",
  "format": "ply",
  "message": "Model generated successfully"
}
```

#### Option 2: Relative path to model file
```json
{
  "success": true,
  "model_path": "/output/model.ply",
  "format": "ply",
  "message": "Model generated successfully"
}
```

#### Option 3: Error response
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

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

## Testing the Integration

### 1. Without Backend (Current State)
- Upload or select demo images
- Preview displays correctly
- Process button shows loading state
- Error message displays when backend not available

### 2. With Backend (Future)
1. Start backend server on `localhost:8000`
2. Ensure endpoint accepts POST to `/process`
3. Return JSON with `model_url` or `model_path`
4. Frontend will automatically load and display 3D model

## Backend Development Notes

### Recommended Workflow
1. Accept single image upload
2. Remove background using Photoroom API
3. Run photogrammetry processing (COLMAP, etc.)
4. Generate PLY or OBJ file
5. Save to accessible location
6. Return URL/path in JSON response

### CORS Configuration
If backend is on different port, ensure CORS headers are set:
```python
# Example for Flask
from flask_cors import CORS
CORS(app)
```

### File Serving
Backend should serve generated model files:
```python
# Example endpoint to serve model files
@app.route('/models/<filename>')
def serve_model(filename):
    return send_from_directory('output_directory', filename)
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

## Example Backend Response Flow

```
1. Frontend sends image
   ↓
2. Backend receives and validates
   ↓
3. Background removal (Photoroom API)
   ↓
4. 3D reconstruction (COLMAP)
   ↓
5. Model generation (PLY/OBJ)
   ↓
6. Save to /output/ directory
   ↓
7. Return JSON with model_url
   ↓
8. Frontend loads and renders model
```

## Contact

If you need any changes to the frontend integration or have questions about the expected formats, update this file or modify the frontend code as needed.

