"""
Local FastAPI server for 3D model generation from images.
Runs TripoSR with CUDA acceleration on the local machine.
"""
import os
import base64
import json
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import torch

from triposr_pipeline import TripoSRPipeline

app = FastAPI(title="3D Model Generation API", version="1.0.0")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
WORK_DIR = Path("/tmp/reconstruction")
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Local output directory for easy access to generated models
LOCAL_OUTPUT_DIR = Path(__file__).parent / "output"
LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Check CUDA availability at startup
CUDA_AVAILABLE = torch.cuda.is_available()
print(f"\n{'='*60}")
print(f"3D Model Generation Server Starting")
print(f"{'='*60}")
print(f"CUDA Available: {CUDA_AVAILABLE}")
if CUDA_AVAILABLE:
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Version: {torch.version.cuda}")
print(f"{'='*60}\n")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "cuda_available": CUDA_AVAILABLE,
        "gpu": torch.cuda.get_device_name(0) if CUDA_AVAILABLE else None,
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "cuda_available": CUDA_AVAILABLE,
        "cuda_version": torch.version.cuda if CUDA_AVAILABLE else None,
        "gpu_name": torch.cuda.get_device_name(0) if CUDA_AVAILABLE else None,
        "gpu_memory": f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB" if CUDA_AVAILABLE else None,
    }


@app.post("/generate")
async def generate_3d_model(
    files: List[UploadFile] = File(...),
    photoroom_api_key: Optional[str] = Form(None),
    include_files: bool = Form(False)
):
    """
    Generate 3D model from uploaded images
    
    Args:
        files: List of image files (up to 5)
        photoroom_api_key: Optional API key for background removal
        include_files: Whether to include base64-encoded output files in response
    
    Returns:
        JSON response with processing results and optional file downloads
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Limit to 5 images
    if len(files) > 5:
        files = files[:5]
    
    image_data = []
    file_info = []
    
    for file in files:
        content = await file.read()
        image_data.append(content)
        file_info.append({
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type
        })
    
    # Use environment variable for API key if not provided
    api_key = photoroom_api_key or os.environ.get("PHOTOROOM_API_KEY")
    
    # Process images
    print(f"\n{'='*60}")
    print(f"Processing {len(image_data)} image(s)")
    print(f"{'='*60}")
    
    # Use TF32 on Ampere+ GPUs for better performance
    if CUDA_AVAILABLE:
        torch.set_float32_matmul_precision('high')
    
    work_dir = WORK_DIR / f"request_{os.getpid()}_{Path(files[0].filename).stem}"
    pipeline = TripoSRPipeline(work_dir, verbose=True)
    result = pipeline.run(image_data, api_key)
    
    # Optionally include base64-encoded files for download
    if include_files and result.get("success"):
        files_content = {}
        for file_path_str in result["triposr"]["files"]:
            file_path = Path(file_path_str)
            if file_path.is_file():
                content = file_path.read_bytes()
                files_content[file_path.name] = base64.b64encode(content).decode('utf-8')
        result["files_base64"] = files_content
    
    return {
        "status": "success" if result.get("success") else "error",
        "files_received": len(files),
        "file_info": file_info,
        "api_key_present": bool(api_key),
        "pipeline_result": result
    }


@app.get("/demo")
async def demo():
    """
    Run demo with pre-loaded images from the img directory
    """
    img_dir = Path(__file__).parent / "img"
    if not img_dir.exists():
        raise HTTPException(status_code=404, detail="Demo image directory not found")
    
    images = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        images.extend(sorted(img_dir.glob(ext)))
    
    if not images:
        raise HTTPException(status_code=404, detail="No demo images found")
    
    # Limit to 5 images
    images = images[:5]
    
    print(f"\n{'='*60}")
    print(f"Running demo with {len(images)} image(s)")
    print(f"{'='*60}")
    for img in images:
        print(f"  - {img.name}")
    
    image_data = [p.read_bytes() for p in images]
    
    # Use TF32 on Ampere+ GPUs
    if CUDA_AVAILABLE:
        torch.set_float32_matmul_precision('high')
    
    work_dir = WORK_DIR / "demo"
    pipeline = TripoSRPipeline(work_dir, verbose=True)
    result = pipeline.run(image_data, None)
    
    return {
        "status": "success" if result.get("success") else "error",
        "source": str(img_dir),
        "files_used": [p.name for p in images],
        "pipeline_result": result,
    }


@app.post("/process")
async def process_image(
    image: UploadFile = File(...),
    photoroom_api_key: Optional[str] = Form(None)
):
    """
    Process a single image and generate a 3D model (frontend-compatible endpoint)
    
    Args:
        image: Single image file
        photoroom_api_key: Optional API key for background removal
    
    Returns:
        JSON response with model_url and format for frontend
    """
    if not image:
        raise HTTPException(status_code=400, detail="No image uploaded")
    
    # Read image content
    content = await image.read()
    image_data = [content]
    
    # Use environment variable for API key if not provided
    api_key = photoroom_api_key or os.environ.get("PHOTOROOM_API_KEY")
    
    # Process image
    print(f"\n{'='*60}")
    print(f"Processing image: {image.filename}")
    print(f"API Key provided: {bool(api_key)}")
    print(f"{'='*60}")
    
    # Use TF32 on Ampere+ GPUs for better performance
    if CUDA_AVAILABLE:
        torch.set_float32_matmul_precision('high')
    
    work_dir = WORK_DIR / f"request_{os.getpid()}_{Path(image.filename).stem}"
    pipeline = TripoSRPipeline(work_dir, verbose=True)
    result = pipeline.run(image_data, api_key)
    
    if not result.get("success"):
        error_msg = result.get("triposr", {}).get("error", "Unknown error during processing")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_msg
            }
        )
    
    # Find the generated model file (GLB, OBJ, or PLY)
    output_files = result.get("triposr", {}).get("files", [])
    model_file = None
    model_format = None
    
    # Prioritize GLB files (new format with textures)
    for file_path in output_files:
        if file_path.endswith('.glb'):
            model_file = Path(file_path)
            model_format = 'glb'
            break
    
    # Fallback to OBJ or PLY if no GLB found
    if not model_file:
        for file_path in output_files:
            if file_path.endswith('.obj'):
                model_file = Path(file_path)
                model_format = 'obj'
                break
            elif file_path.endswith('.ply'):
                model_file = Path(file_path)
                model_format = 'ply'
                break
    
    if not model_file or not model_file.exists():
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "No 3D model file generated"
            }
        )
    
    # Copy model and related files to local output directory
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_filename = f"{Path(image.filename).stem}_{timestamp}.{model_format}"
    local_model_path = LOCAL_OUTPUT_DIR / local_filename
    
    try:
        # Copy the main model file
        shutil.copy2(model_file, local_model_path)
        print(f"✓ Saved model to: {local_model_path}")
        
        # Also copy any associated files (e.g., .mtl for .obj files)
        if model_format == 'obj':
            model_dir = model_file.parent
            mtl_file = model_dir / model_file.name.replace('.obj', '.mtl')
            if mtl_file.exists():
                local_mtl_path = LOCAL_OUTPUT_DIR / f"{Path(image.filename).stem}_{timestamp}.mtl"
                shutil.copy2(mtl_file, local_mtl_path)
                print(f"✓ Saved material to: {local_mtl_path}")
    except Exception as e:
        print(f"Warning: Could not copy to local output: {e}")
    
    # Return URL to access the model
    model_url = f"http://localhost:8000/models/{model_file.name}"
    
    return {
        "success": True,
        "model_url": model_url,
        "format": model_format,
        "message": "Model generated successfully",
        "local_path": str(local_model_path) if local_model_path.exists() else None
    }


@app.get("/models/{filename}")
async def serve_model(filename: str):
    """
    Serve generated 3D model files
    """
    # Search in work directory for the file (including subdirectories)
    for result_dir in WORK_DIR.glob("*/triposr_output"):
        # Check directly in triposr_output
        file_path = result_dir / filename
        if file_path.exists() and file_path.is_file():
            # Determine media type based on extension
            media_type = "application/octet-stream"
            if filename.endswith('.glb'):
                media_type = "model/gltf-binary"
            elif filename.endswith('.obj'):
                media_type = "model/obj"
            elif filename.endswith('.ply'):
                media_type = "model/ply"
            elif filename.endswith('.mtl'):
                media_type = "model/mtl"
            
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type=media_type
            )
        
        # Also check in subdirectories (TripoSR creates numbered subdirs like 0/, 1/, etc.)
        for subdir in result_dir.glob("*/"):
            file_path = subdir / filename
            if file_path.exists() and file_path.is_file():
                media_type = "application/octet-stream"
                if filename.endswith('.glb'):
                    media_type = "model/gltf-binary"
                elif filename.endswith('.obj'):
                    media_type = "model/obj"
                elif filename.endswith('.ply'):
                    media_type = "model/ply"
                elif filename.endswith('.mtl'):
                    media_type = "model/mtl"
                
                return FileResponse(
                    path=str(file_path),
                    filename=filename,
                    media_type=media_type
                )
    
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a generated file
    Note: This is a simple implementation. For production, implement proper file management and security.
    """
    # Search in work directory for the file
    for result_dir in WORK_DIR.glob("*/triposr_output"):
        file_path = result_dir / filename
        if file_path.exists() and file_path.is_file():
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/octet-stream"
            )
    
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"\nStarting server on {host}:{port}")
    print(f"CUDA Available: {CUDA_AVAILABLE}\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

