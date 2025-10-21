
from pathlib import Path
from pipeline import PhotogrammetryPipeline
import sys

def test_pipeline_locally():
    # Test the pipeline OUTSIDE of Modal

    # Setup
    img_testing_dir = Path(__file__).parent / "img_testing"
    work_dir = Path(__file__).parent / "local_test_output"
    
    # Clean up previous test
    if work_dir.exists():
        import shutil
        shutil.rmtree(work_dir)
    
    work_dir.mkdir(exist_ok=True)
    
    # Find test images
    test_images = list(img_testing_dir.glob("*.jpg"))
    
    if not test_images:
        print(" - No test images found in img_testing folder")
        print(f" Looking in: {img_testing_dir.absolute()}")
        return
    
    print(f"\n{'='*60}")
    print(f"LOCAL PIPELINE TEST")
    print(f"{'='*60}\n")
    print(f"Found {len(test_images)} test images:")
    for img in test_images:
        print(f"  - {img.name} ({img.stat().st_size:,} bytes)")
    
    # Load image data
    print(f"\nLoading images into memory...")
    image_data = []
    for img_path in test_images:
        with open(img_path, 'rb') as f:
            image_data.append(f.read())
    
    print(f"✓ Loaded {len(image_data)} images\n")
    
    # Create and run pipeline
    try:
        pipeline = PhotogrammetryPipeline(work_dir)
        result = pipeline.run_test_pipeline(image_data)
        
        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}\n")
        
        for key, value in result.items():
            print(f"{key}: {value}")
        
        print(f"\n :D Local test completed successfully!")
        print(f"\nOutput directory: {work_dir.absolute()}")
        print(f"You can inspect the files there.\n")
        
        return result
        
    except Exception as e:
        print(f"\n :( Pipeline failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Check if COLMAP is installed
    import subprocess
    try:
        result = subprocess.run(
            ["colmap", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ COLMAP found: {result.stdout.strip()}\n")
    except FileNotFoundError:
        print(" - COLMAP not found, install it first")

        sys.exit(1)
    except Exception as e:
        print(f"Could not verify COLMAP: {e}\n")
    
    test_pipeline_locally()