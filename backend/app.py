import modal
from pathlib import Path

app = modal.App("photogrammetry-poc-backend")

image = modal.Image.debian_slim(python_version="3.11").pip_install_from_requirements(
    "backend/requirements.txt"
)

@app.function(image=image)
@modal.asgi_app()
def upload_test():
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException
    from typing import List, Optional
    
    web_app = FastAPI()
    
    @web_app.post("/")
    async def upload_endpoint(
        files: List[UploadFile] = File(...),
        photoroom_api_key: Optional[str] = Form(None)
    ):
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        # Process files
        file_info = []
        for file in files:
            content = await file.read()
            file_info.append({
                "filename": file.filename,
                "size": len(content),
                "content_type": file.content_type
            })
        
        return {
            "status": "success",
            "files_received": len(files),
            "file_info": file_info,
            "api_key_present": bool(photoroom_api_key)
        }
    
    return web_app

@app.local_entrypoint()
def main():
    """Test the upload endpoint with a local image"""
    import httpx
    
    # Try to find test images in the img_testing folder
    img_testing_dir = Path(__file__).parent / "img_testing"
    test_image_paths = list(img_testing_dir.glob("*.png"))
    
    test_image = None
    for img_path in test_image_paths:
        if img_path.exists():
            test_image = img_path
            break
    
    if not test_image:
        print("No test image found.")
        return
    
    print(f"Testing upload with: {test_image}")
    print(f"Image size: {test_image.stat().st_size} bytes")
    
    # Get the deployed URL
    upload_url = upload_test.web_url
    print(f"Uploading to: {upload_url}")
    
    # Test upload w dummy api key
    with open(test_image, "rb") as f:
        files = {"files": (test_image.name, f, "image/png")}
        data = {"photoroom_api_key": "test_api_key_123"}
        
        response = httpx.post(upload_url, files=files, data=data)
        
    print(f"\nResponse status: {response.status_code}")
    print(f"Response body: {response.json()}")
    
    return response.json()