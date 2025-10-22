import os
import modal
from pathlib import Path
from typing import Optional

app = modal.App("3dgen-poc-backend")

# GPU-enabled base; install TripoSR and backend deps
image = (
    modal.Image.from_registry("nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04", add_python="3.11")
    .apt_install(
        "git",
        "build-essential",
        "cmake",
        "ninja-build",
        # OpenGL/Mesa libraries for moderngl texture baking
        "libgl1-mesa-glx",
        "libgl1-mesa-dri",
        "libglib2.0-0",
        "libsm6",
        "libxrender1",
        "libxext6",
        # Virtual display for headless OpenGL rendering
        "xvfb",
    )
    .run_commands(
        "pip install --upgrade pip",
        # Install CUDA-enabled Torch explicitly for CUDA 12.1
        "pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121",
        # Install onnxruntime-gpu for CUDA acceleration (required by rembg in TripoSR)
        "pip install onnxruntime-gpu",
        # Install additional dependencies for TripoSR utils
        "pip install imageio omegaconf",
        # Clone TripoSR to a known location
        "git clone https://github.com/VAST-AI-Research/TripoSR.git /root/TripoSR || true",
        # Install TripoSR requirements with CUDA arch flags for T4 (7.5), A10G (8.6), and common GPUs
        # TORCH_CUDA_ARCH_LIST ensures torchmcubes builds kernels for the right GPU architectures
        'export CXX=g++; export CUDA_HOME=/usr/local/cuda; export PATH=$PATH:/usr/local/cuda/bin; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64; export TORCH_CUDA_ARCH_LIST="7.0 7.5 8.0 8.6"; pip install -r /root/TripoSR/requirements.txt --no-cache-dir',
    )
    .pip_install_from_requirements("backend/requirements.txt")
    .add_local_file("backend/triposr_pipeline.py", "/root/triposr_pipeline.py")
    .add_local_file("backend/background_removal.py", "/root/background_removal.py")
    .add_local_dir("backend/img_testing0", "/root/img_testing0")
)


@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=600,
    secrets=[modal.Secret.from_name("photoroom-api")]
)
def process_images(image_data: list[bytes], photoroom_api_key: Optional[str] = None) -> dict:
    from pathlib import Path
    from triposr_pipeline import TripoSRPipeline

    # Use provided key or fall back to Modal secret
    if photoroom_api_key is None:
        photoroom_api_key = os.environ.get("PHOTOROOM_API_KEY")

    work_dir = Path("/tmp/reconstruction")
    pipeline = TripoSRPipeline(work_dir)
    return pipeline.run(image_data, photoroom_api_key)

@app.function(image=image)
@modal.asgi_app()
def web_app():
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException
    from typing import List, Optional
    
    app = FastAPI()
    
    @app.post("/")
    async def upload(
        files: List[UploadFile] = File(...),
        photoroom_api_key: Optional[str] = Form(None)
    ):
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
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
        # Limit to 5 images as per design
        if len(image_data) > 5:
            image_data = image_data[:5]

        result = process_images.remote(image_data, photoroom_api_key)
        
        return {
            "status": "success",
            "files_received": len(files),
            "file_info": file_info,
            "api_key_present": bool(photoroom_api_key),
            "pipeline_result": result
        }

    @app.get("/demo")
    async def demo():
        from pathlib import Path
        from fastapi import HTTPException

        img_dir = Path("/root/img_testing0")
        if not img_dir.exists():
            raise HTTPException(status_code=404, detail="Demo image directory not found")

        images = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            images.extend(img_dir.glob(ext))

        if not images:
            raise HTTPException(status_code=404, detail="No demo images found")

        image_data = [p.read_bytes() for p in images[:5]]

        result = process_images.remote(image_data, None)

        return {
            "status": "success",
            "source": "/root/img_testing0",
            "files_used": [p.name for p in images[:5]],
            "pipeline_result": result,
        }
    
    return app


@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=600,
    secrets=[modal.Secret.from_name("photoroom-api")]
)
def download_output_files(image_data: list[bytes], photoroom_api_key: Optional[str] = None):
    """Process images and return the generated 3D model files as bytes"""
    from pathlib import Path
    from triposr_pipeline import TripoSRPipeline
    import base64
    
    # Use provided key or fall back to Modal secret
    if photoroom_api_key is None:
        photoroom_api_key = os.environ.get("PHOTOROOM_API_KEY")
    
    work_dir = Path("/tmp/reconstruction")
    pipeline = TripoSRPipeline(work_dir)
    result = pipeline.run(image_data, photoroom_api_key)
    
    if not result.get("success"):
        return result
    
    # Read generated files and encode as base64
    files_content = {}
    for file_path_str in result["triposr"]["files"]:
        file_path = Path(file_path_str)
        if file_path.is_file():
            content = file_path.read_bytes()
            # Store as base64 for JSON serialization
            files_content[file_path.name] = base64.b64encode(content).decode('utf-8')
    
    result["files_base64"] = files_content
    return result


@app.local_entrypoint()
def main():
    """Local entry point - reads local demo images and processes on Modal GPU"""
    import json
    import base64
    
    # Read demo images from local directory
    img_dir = Path(__file__).parent / "img_testing0"
    
    if not img_dir.exists():
        print(f"❌ Demo image directory not found: {img_dir}")
        return
    
    images = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        images.extend(img_dir.glob(ext))
    
    if not images:
        print(f"❌ No demo images found in {img_dir}")
        return
    
    print(f"\n{'='*60}")
    print(f"Running demo with {len(images)} image(s) on Modal GPU")
    print(f"{'='*60}")
    for img in images:
        print(f"  - {img.name}")
    
    # Read image bytes locally
    image_data = [p.read_bytes() for p in images[:5]]
    
    # Process on Modal GPU and download files
    print("\nInvoking process_images() on Modal GPU...")
    result = download_output_files.remote(image_data, None)
    
    # Save downloaded files locally
    if result.get("success") and "files_base64" in result:
        output_dir = Path(__file__).parent / "local_output"
        output_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*60}")
        print("DOWNLOADING FILES")
        print(f"{'='*60}")
        
        for filename, content_b64 in result["files_base64"].items():
            content = base64.b64decode(content_b64)
            output_path = output_dir / filename
            output_path.write_bytes(content)
            print(f"✓ Saved: {output_path}")
        
        # Remove base64 data from result for cleaner display
        file_list = list(result["files_base64"].keys())
        del result["files_base64"]
        
        print(f"\n{'='*60}")
        print("DEMO RESULT")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2))
        print(f"\n✅ Demo completed successfully!")
        print(f"\n📁 Output files saved to: {output_dir.absolute()}")
        print(f"   Files: {', '.join(file_list)}")
    else:
        print("\n" + "="*60)
        print("DEMO RESULT")
        print("="*60)
        print(json.dumps(result, indent=2))
        print("\n❌ Demo failed. Check error above.")
    
    return result