import subprocess
from pathlib import Path
from typing import List

class PhotogrammetryPipeline:
    """Handles the complete photogrammetry pipeline"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.img_dir = self.work_dir / "images"
        self.colmap_dir = self.work_dir / "colmap"
        self.output_dir = self.work_dir / "output"
        
        # Create directories
        for d in [self.img_dir, self.colmap_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def save_images(self, image_data: List[bytes]) -> None:
        """Save uploaded images to disk"""
        print(f"Saving {len(image_data)} images...")
        
        for i, data in enumerate(image_data):
            img_path = self.img_dir / f"image_{i:03d}.jpg"
            img_path.write_bytes(data)
        
        print(f"✓ Saved {len(image_data)} images to {self.img_dir}")
    
    def run_feature_extraction(self) -> dict:
        """Run COLMAP feature extraction"""
        print("Running COLMAP feature extraction...")
        
        db_path = self.colmap_dir / "database.db"
        
        try:
            result = subprocess.run([
                "colmap", "feature_extractor",
                "--database_path", str(db_path),
                "--image_path", str(self.img_dir),
                "--ImageReader.single_camera", "1",
                "--ImageReader.camera_model", "SIMPLE_RADIAL",
                "--SiftExtraction.use_gpu", "0"
            ], check=True, capture_output=True, text=True)
            
            print("✓ Feature extraction complete")
            
            return {
                "success": True,
                "database_path": str(db_path),
                "database_exists": db_path.exists(),
                "database_size": db_path.stat().st_size if db_path.exists() else 0
            }
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Feature extraction failed")
            print(f"Error: {e.stderr}")
            return {
                "success": False,
                "error": e.stderr
            }
    
    def run_test_pipeline(self, image_data: List[bytes]) -> dict:
        """Test pipeline with COLMAP feature extraction"""
        print("\n" + "="*50)
        print("Starting Test Pipeline with COLMAP")
        print("="*50 + "\n")
        
        self.save_images(image_data)
        
        # Run feature extraction
        colmap_result = self.run_feature_extraction()
        
        # Count saved files
        saved_files = list(self.img_dir.glob("*.jpg"))
        
        print("\n" + "="*50)
        print("Test Pipeline Complete!")
        print("="*50 + "\n")
        
        return {
            "images_saved": len(saved_files),
            "work_directory": str(self.work_dir),
            "image_directory": str(self.img_dir),
            "colmap_directory": str(self.colmap_dir),
            "output_directory": str(self.output_dir),
            "colmap_feature_extraction": colmap_result
        }