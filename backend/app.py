import modal
from pathlib import Path

app = modal.App("photogrammetry-poc-backend")

# Use COLMAP docker image as base, then add Python
image = (
    modal.Image.from_registry("colmap/colmap:latest", add_python="3.11")
    .pip_install_from_requirements("backend/requirements.txt")
    .add_local_file("backend/pipeline.py", "/root/pipeline.py")
)

@app.function(image=image, cpu=2, memory=2048, timeout=300)
def process_images(image_data: list[bytes]) -> dict:
    from pathlib import Path
    from pipeline import PhotogrammetryPipeline
    
    pipeline = PhotogrammetryPipeline(Path("/tmp/reconstruction"))
    return pipeline.run_test_pipeline(image_data)

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
        
        result = process_images.remote(image_data)
        
        return {
            "status": "success",
            "files_received": len(files),
            "file_info": file_info,
            "api_key_present": bool(photoroom_api_key),
            "pipeline_result": result
        }
    
    return app

@app.local_entrypoint()
def test():
    import httpx
    import json
    
    img_dir = Path(__file__).parent / "img_testing"
    images = list(img_dir.glob("*.jpg"))
    
    if not images:
        print("No test images found")
        return
    
    print(f"\nTesting with {len(images)} images:")
    for img in images:
        print(f"  - {img.name}")
    
    files = [("files", (img.name, open(img, "rb"), "image/png")) for img in images]
    data = {"photoroom_api_key": "test_key"}
    
    try:
        response = httpx.post(
            web_app.get_web_url(),
            files=files,
            data=data,
            timeout=60.0
        )
        print(f"\nStatus: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return response.json()
    finally:
        for _, (_, f, _) in files:
            f.close()