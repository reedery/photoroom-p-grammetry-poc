# test file for Modal.com
import modal

app = modal.App("modal-test-app")

@app.function()
def hello(name: str):
    # will print to the terminal and in the browser 
    print(f"Hello from hello()")
    return f"Hello, {name}!"

@app.local_entrypoint()
def main():
    result = hello.remote("World")
    # will print to the terminal locally, not in the browser
    print(result + "- This code is running on a remote worker!")
