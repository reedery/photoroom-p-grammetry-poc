from pathlib import Path
from typing import List

class PhotogrammetryPipeline:
    """Handles the complete photogrammetry pipeline"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.img_dir = self.work_dir / "images"
        self.output_dir = self.work_dir / "output"
        
        # Create directories
        for d in [self.img_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def save_images(self, image_data: List[bytes]) -> None:
        """Save uploaded images to disk"""
        print(f"Saving {len(image_data)} images...")
        
        for i, data in enumerate(image_data):
            img_path = self.img_dir / f"image_{i:03d}.jpg"
            img_path.write_bytes(data)
        
        print(f"✓ Saved {len(image_data)} images to {self.img_dir}")
    
    def run_test_pipeline(self, image_data: List[bytes]) -> dict:
        """Test pipeline that just saves images and returns info"""
        print("\n" + "="*50)
        print("Starting Test Pipeline")
        print("="*50 + "\n")
        
        self.save_images(image_data)
        
        # Create a test output file
        test_file = self.output_dir / "test.txt"
        test_file.write_text(f"Processed {len(image_data)} images successfully!")
        
        # Count saved files
        saved_files = list(self.img_dir.glob("*.jpg"))
        
        print("\n" + "="*50)
        print("Test Pipeline Complete!")
        print("="*50 + "\n")
        
        return {
            "images_saved": len(saved_files),
            "work_directory": str(self.work_dir),
            "image_directory": str(self.img_dir),
            "output_directory": str(self.output_dir)
        }
        