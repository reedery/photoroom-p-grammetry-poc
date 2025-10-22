import modal
from pathlib import Path

app = modal.App("photogrammetry-poc-backend")

# Use NVIDIA CUDA base image and install COLMAP with GPU support
# The official colmap/colmap:latest image is CPU-only
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.6.0-devel-ubuntu22.04",  # Updated to non-deprecated version
        add_python="3.11"
    )
    .apt_install(
        # COLMAP build dependencies
        "git", "cmake", "ninja-build", "build-essential",
        "libboost-program-options-dev", "libboost-filesystem-dev",
        "libboost-graph-dev", "libboost-system-dev",
        "libeigen3-dev", "libflann-dev", "libfreeimage-dev",
        "libmetis-dev", "libgoogle-glog-dev", "libgtest-dev",
        "libsqlite3-dev", "libglew-dev", "qtbase5-dev",
        "libqt5opengl5-dev", "libcgal-dev", "libceres-dev",
        "wget"
    )
    .run_commands(
        # Build COLMAP from source with CUDA support
        "cd /tmp && git clone https://github.com/colmap/colmap.git",
        "cd /tmp/colmap && git checkout 3.9.1",  # Use stable version
        "cd /tmp/colmap && mkdir build && cd build",
        'cd /tmp/colmap/build && cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES="75;80;86"',
        "cd /tmp/colmap/build && ninja && ninja install",
        "rm -rf /tmp/colmap"
    )
    .pip_install_from_requirements("backend/requirements.txt")
    .add_local_file("backend/pipeline.py", "/root/pipeline.py")
    .add_local_file("backend/bg_removal.py", "/root/bg_removal.py")
)

@app.function(
    image=image, 
    gpu="T4",  # NVIDIA T4 GPU for CUDA-accelerated dense reconstruction
    memory=8192,  # 8GB RAM for GPU workload
    timeout=7200,  # 2 hours - plenty of time for large batches
    scaledown_window=300  # Keep container alive for 5 min after completion
)
def process_images_async(image_data: list[bytes], photoroom_api_key: str = None, mask_data: list[bytes] = None) -> dict:
    """Process images and return the 3D model with full GPU acceleration (async job)
    
    Architecture:
    - SfM (feature extraction/matching): GPU-accelerated SIFT
    - Dense reconstruction (MVS): GPU/CUDA (patch match stereo)
    - Mesh generation: CPU (Open3D)
    
    Args:
        image_data: List of image bytes
        photoroom_api_key: Optional API key for generating masks
        mask_data: Optional pre-generated masks (skips API call if provided)
    
    Returns:
        dict with mesh_bytes and metadata
    
    All COLMAP steps use GPU when available for maximum performance.
    """
    from pathlib import Path
    from pipeline import PhotogrammetryPipeline
    import time
    import subprocess
    
    start_time = time.time()
    
    # Verify GPU is available
    print("\n" + "="*60, flush=True)
    print("GPU VERIFICATION", flush=True)
    print("="*60, flush=True)
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ GPU detected: {result.stdout.strip()}", flush=True)
        else:
            print(f"⚠️  nvidia-smi failed: {result.stderr}", flush=True)
    except Exception as e:
        print(f"⚠️  Could not verify GPU: {e}", flush=True)
    
    print("="*60 + "\n", flush=True)
    
    # cpu_only=False enables full GPU acceleration:
    # - Feature extraction: GPU-accelerated SIFT
    # - Feature matching: GPU-accelerated matching
    # - Dense reconstruction (MVS): CUDA-required patch match stereo
    pipeline = PhotogrammetryPipeline(Path("/tmp/reconstruction"), cpu_only=False)
    result = pipeline.run_full_pipeline(image_data, photoroom_api_key, pre_generated_masks=mask_data)
    
    if not result["success"]:
        return {
            "success": False,
            "error": f"Pipeline failed at stage: {result.get('stage', 'unknown')}",
            "details": result
        }
    
    # Read the mesh file
    mesh_path = Path(result["output_mesh_path"])
    mesh_bytes = mesh_path.read_bytes()
    
    elapsed_time = time.time() - start_time
    
    return {
        "success": True,
        "mesh_bytes": mesh_bytes,
        "processing_time": elapsed_time,
        "images_processed": result.get("images_saved", 0),
        "masks_used": result.get("binary_masks", 0),
        "vertices": result.get("mesh_generation", {}).get("vertices", 0),
        "triangles": result.get("mesh_generation", {}).get("triangles", 0)
    }

@app.function(image=image)
@modal.asgi_app()
def web_app():
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException
    from fastapi.responses import Response
    from typing import List, Optional
    
    app = FastAPI()
    
    @app.post("/")
    async def upload(
        files: List[UploadFile] = File(...),
        photoroom_api_key: Optional[str] = Form(None),
        mask_files: List[UploadFile] = File(default=[])
    ):
        """Start async processing job and return job ID immediately"""
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        if len(files) < 3:
            raise HTTPException(status_code=400, detail="Need at least 3 images")
        
        image_data = []
        for file in files:
            content = await file.read()
            image_data.append(content)
        
        # Read mask files if provided
        mask_data = None
        if mask_files and len(mask_files) > 0:
            mask_data = []
            for file in mask_files:
                content = await file.read()
                mask_data.append(content)
            print(f"Starting job for {len(files)} images with {len(mask_data)} pre-generated masks...")
        else:
            print(f"Starting job for {len(files)} images...")
        
        # Spawn async job - returns immediately
        try:
            job = process_images_async.spawn(image_data, photoroom_api_key, mask_data)
            job_id = job.object_id
            
            print(f"Job {job_id} started")
            
            return {
                "job_id": job_id,
                "status": "started",
                "message": "Processing job started. Poll /status/{job_id} for progress.",
                "images": len(image_data),
                "masks": len(mask_data) if mask_data else 0
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/status/{job_id}")
    async def get_status(job_id: str):
        """Check job status"""
        try:
            from modal.functions import FunctionCall
            
            function_call = FunctionCall.from_id(job_id)
            
            try:
                # Try to get result - will raise if not done
                result = function_call.get(timeout=0)
                
                if result["success"]:
                    return {
                        "status": "completed",
                        "job_id": job_id,
                        "processing_time": result.get("processing_time"),
                        "images_processed": result.get("images_processed"),
                        "masks_used": result.get("masks_used"),
                        "vertices": result.get("vertices"),
                        "triangles": result.get("triangles")
                    }
                else:
                    return {
                        "status": "failed",
                        "job_id": job_id,
                        "error": result.get("error")
                    }
                    
            except TimeoutError:
                # Job still running
                return {
                    "status": "running",
                    "job_id": job_id,
                    "message": "Job is still processing..."
                }
                
        except Exception as e:
            return {
                "status": "error",
                "job_id": job_id,
                "error": str(e)
            }
    
    @app.get("/result/{job_id}")
    async def get_result(job_id: str):
        """Get the final mesh file (blocks until complete)"""
        try:
            from modal.functions import FunctionCall
            
            function_call = FunctionCall.from_id(job_id)
            result = function_call.get()  # Blocks until done
            
            if not result["success"]:
                raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
            
            # Return the mesh file
            return Response(
                content=result["mesh_bytes"],
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": "attachment; filename=model.obj",
                    "Access-Control-Allow-Origin": "*"
                }
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

@app.local_entrypoint()
def test(num_images: int = None):
    """Test the Modal deployment with images from img_testing{number}/
    
    Args:
        num_images: Limit to first N images for faster testing (default: all images)
    """
    import httpx
    import os
    
    img_dir = Path(__file__).parent / "img_testing3"
    images = sorted(list(img_dir.glob("*.jpg")))
    
    if not images:
        print("❌ No test images found in img_testing3/")
        print(f"   Looking in: {img_dir.absolute()}")
        return
    
    # Check for pre-generated masks (e.g., img_testing3_masks/)
    masks_dir = img_dir.parent / f"{img_dir.name}_masks"
    has_masks = masks_dir.exists()
    
    # Limit number of images if specified
    if num_images:
        images = images[:num_images]
        print(f"\n⚠️  Limited to first {num_images} images for testing")
    
    print(f"\n{'='*60}")
    print(f"Testing Modal Deployment with {len(images)} images")
    print(f"{'='*60}\n")
    
    for img in images[:5]:  # Show first 5
        print(f"  📷 {img.name}")
    if len(images) > 5:
        print(f"  ... and {len(images) - 5} more")
    
    # Check for pre-generated masks
    masks = []
    if has_masks:
        # Match masks to images by stem name
        for img in images:
            mask_path = masks_dir / f"{img.stem}.png"
            if mask_path.exists():
                masks.append(mask_path)
        
        if masks:
            print(f"\n✅ Found {len(masks)} pre-generated masks in {masks_dir.name}/")
            print(f"   Skipping Photoroom API calls")
        else:
            has_masks = False
    
    # Get API key from environment (only needed if no pre-generated masks)
    api_key = os.environ.get("PHOTOROOM_API_KEY")
    if has_masks:
        print(f"\n⏭️  Photoroom API key not needed (using pre-generated masks)")
        api_key = None
    elif api_key:
        print(f"\n✅ Photoroom API key found (length: {len(api_key)})")
        print(f"   Backgrounds will be removed via API")
    else:
        print(f"\n⚠️  No PHOTOROOM_API_KEY environment variable found")
        print(f"   No pre-generated masks available")
        print(f"   Reconstruction will proceed WITHOUT masks")
        print(f"   Set with: export PHOTOROOM_API_KEY='your_key'\n")
    
    # Build files list with images
    files_to_upload = [("files", (img.name, open(img, "rb"), "image/jpeg")) for img in images]
    
    # Add mask files if available
    if masks:
        files_to_upload.extend([("mask_files", (mask.name, open(mask, "rb"), "image/png")) for mask in masks])
    
    data = {"photoroom_api_key": api_key} if api_key else {}
    
    try:
        base_url = web_app.get_web_url()
        
        # Step 1: Upload files and start job (fast - returns immediately)
        print(f"\n📤 Uploading to Modal endpoint...")
        print(f"   URL: {base_url}")
        print(f"   Uploading {len(images)} images...")
        
        response = httpx.post(
            base_url,
            files=files_to_upload,
            data=data,
            timeout=120  # Upload should be quick, just need time for file transfer
        )
        
        if response.status_code != 200:
            print(f"\n{'='*60}")
            print(f"❌ Upload Error: {response.status_code}")
            print(f"{'='*60}")
            print(response.text)
            return
        
        job_info = response.json()
        job_id = job_info["job_id"]
        
        print(f"\n✅ Upload complete!")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {job_info['status']}")
        
        # Step 2: Poll for status
        print(f"\n⏳ Processing started...")
        print(f"   Estimated time: 20-40 minutes for {len(images)} images")
        print(f"   - SfM: ~2-3 min (GPU-accelerated)")
        if has_masks:
            print(f"   - Using pre-generated masks (skipping API)")
        else:
            print(f"   - Mask generation: ~{len(images) * 2 // 60} min ({len(images)} images)")
        print(f"   - Dense reconstruction (MVS): ~10-30 min (most intensive)")
        print(f"   - Mesh generation: ~1-2 min\n")
        
        import time
        status_url = f"{base_url}/status/{job_id}"
        poll_interval = 10  # seconds
        start_poll_time = time.time()
        
        print(f"💡 Tip: Watch live logs at https://modal.com/apps (look for job {job_id[:16]}...)\n")
        
        while True:
            try:
                status_response = httpx.get(status_url, timeout=30)
                status_data = status_response.json()
                
                current_status = status_data["status"]
                elapsed = time.time() - start_poll_time
                
                if current_status == "completed":
                    print(f"\n✅ Job completed!")
                    print(f"   Processing time: {status_data.get('processing_time', 0):.1f}s ({status_data.get('processing_time', 0)/60:.1f} min)")
                    print(f"   Images: {status_data.get('images_processed')}")
                    print(f"   Masks: {status_data.get('masks_used')}")
                    print(f"   Vertices: {status_data.get('vertices'):,}")
                    print(f"   Triangles: {status_data.get('triangles'):,}")
                    break
                    
                elif current_status == "failed":
                    print(f"\n❌ Job failed!")
                    print(f"   Error: {status_data.get('error')}")
                    return
                    
                elif current_status == "running":
                    print(f"⏳ Still processing... [{elapsed:.0f}s elapsed] (checking again in {poll_interval}s)", flush=True)
                    time.sleep(poll_interval)
                    
                else:
                    print(f"⚠️  Unknown status: {current_status} [{elapsed:.0f}s elapsed]")
                    time.sleep(poll_interval)
                    
            except httpx.ReadTimeout:
                print(f"⏳ Status check timed out (job still running) [{elapsed:.0f}s elapsed]... checking again", flush=True)
                time.sleep(poll_interval)
        
        # Step 3: Download result
        print(f"\n📥 Downloading mesh...")
        result_url = f"{base_url}/result/{job_id}"
        
        result_response = httpx.get(result_url, timeout=60)
        
        if result_response.status_code == 200:
            output_path = Path(__file__).parent / "model_from_modal.obj"
            output_path.write_bytes(result_response.content)
            print(f"\n{'='*60}")
            print(f"✅ SUCCESS!")
            print(f"{'='*60}")
            print(f"Model saved to: {output_path}")
            print(f"File size: {len(result_response.content):,} bytes")
            print(f"\nYou can view the model in:")
            print(f"  - Blender")
            print(f"  - MeshLab")
            print(f"  - Online: https://3dviewer.net\n")
        else:
            print(f"\n{'='*60}")
            print(f"❌ Download Error: {result_response.status_code}")
            print(f"{'='*60}")
            print(result_response.text)
            
    finally:
        for _, (_, f, _) in files_to_upload:
            f.close()
            