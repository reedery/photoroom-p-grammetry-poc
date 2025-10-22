import os
import modal
from pathlib import Path
from typing import Optional

app = modal.App("3dgen-poc-backend")

# GPU-enabled base; install TripoSR and backend deps
# Note: Using -devel (not -runtime) because we compile torchmcubes from source
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
        # Install CUDA-enabled Torch explicitly for CUDA 12.1 (pinned version)
        "pip install torch==2.5.1 torchvision --index-url https://download.pytorch.org/whl/cu121",
        # Install onnxruntime-gpu for CUDA acceleration (pinned version)
        "pip install onnxruntime-gpu==1.20.1",
        # Install additional dependencies for TripoSR utils (pinned versions)
        "pip install imageio==2.36.1 omegaconf==2.3.0",
        # Shallow clone TripoSR to save time and bandwidth
        "git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git /root/TripoSR",
        # Install TripoSR requirements with CUDA arch flag for L40S (8.9)
        # Only compile for L40S to speed up image build (75% faster than 4 archs)
        'export CXX=g++; export CUDA_HOME=/usr/local/cuda; export PATH=$PATH:/usr/local/cuda/bin; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64; export TORCH_CUDA_ARCH_LIST="8.9"; pip install -r /root/TripoSR/requirements.txt --no-cache-dir',
    )
    .pip_install_from_requirements("backend/requirements.txt")
    .add_local_file("backend/triposr_pipeline.py", "/root/triposr_pipeline.py")
    .add_local_file("backend/background_removal.py", "/root/background_removal.py")
    .add_local_dir("backend/img", "/root/img")
)


MINUTE = 60

# Fast boot trades startup time for slightly slower inference
# True: Fast cold starts (~30s), good for web apps with scaledown_window
# False: Slow cold starts (~90s), best inference speed
FAST_BOOT = True

@app.function(
    image=image,
    gpu="L40S",  # Ada Lovelace arch, 48GB VRAM, excellent price/performance
    memory=16384,  # 16GB for model + textures
    timeout= 5 * MINUTE,  # Container startup + processing time
    scaledown_window= 5 * MINUTE,  
    secrets=[modal.Secret.from_name("photoroom-api")],
)
@modal.concurrent(max_inputs=4)  # Process up to 4 requests simultaneously
def process_images(image_data: list[bytes], photoroom_api_key: Optional[str] = None, include_files: bool = False) -> dict:
    from pathlib import Path
    from triposr_pipeline import TripoSRPipeline
    import base64
    import torch

    # Fast boot optimization: disable PyTorch compilation for faster startup
    if FAST_BOOT:
        torch.set_float32_matmul_precision('high')  # Use TF32 on Ampere+ GPUs
        torch._dynamo.config.suppress_errors = True  # Skip dynamo compilation
        
    # Use provided key or fall back to Modal secret
    if photoroom_api_key is None:
        photoroom_api_key = os.environ.get("PHOTOROOM_API_KEY")

    work_dir = Path("/tmp/reconstruction")
    pipeline = TripoSRPipeline(work_dir)
    result = pipeline.run(image_data, photoroom_api_key)
    
    # Optionally include base64-encoded files for download
    if include_files and result.get("success"):
        files_content = {}
        for file_path_str in result["triposr"]["files"]:
            file_path = Path(file_path_str)
            if file_path.is_file():
                content = file_path.read_bytes()
                files_content[file_path.name] = base64.b64encode(content).decode('utf-8')
        result["files_base64"] = files_content
    
    return result

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


@app.local_entrypoint()
def main():
    """Local entry point - reads local demo images and processes on Modal GPU"""
    import json
    import base64
    
    # Read demo images from local directory
    img_dir = Path(__file__).parent / "img"
    
    if not img_dir.exists():
        print(f"❌ Demo image directory not found: {img_dir}")
        return
    
    # Look specifically for mug.jpg first, then any other images
    mug_image = img_dir / "mug.jpg"
    if mug_image.exists():
        images = [mug_image]
    else:
        images = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.heic", "*.HEIC"):
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
    result = process_images.remote(image_data, None, include_files=True)
    
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