import modal

app = modal.App("photogrammetry-demo")

image = modal.Image.debian_slim(python_version="3.11")

@app.function(image=image)
@modal.web_endpoint(method="GET")
def hello():
    return {"message": "Hello from Modal!"}