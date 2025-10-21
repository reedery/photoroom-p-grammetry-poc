# Photogrammetry POC Backend

Modal-based python backend for processing images

Pipeline (TODO)

- Images resized (todo) then uploaded (done)
- Images aligned with sfm (todo)
- Images BG removed (todo)
- Images merged to form 3D model vis photogram (todo)
- Setup img uploader in front end (todo)
- Display final 3D model in front end (todo)

## Setup

```bash
pip install -r backend/requirements.txt
```

### Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
modal deploy backend/app.py
```

## Modal Commands

### Run in development (auto-reload)

```bash
modal serve backend/app.py
```

### Test locally

```bash
modal run backend/app.py
```

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

## Functions

- `process_images`: Modal function that processes uploaded images
- `web_app`: FastAPI ASGI app serving the upload endpoint
- `test`: Local entrypoint for testing with images from `img_testing/`
