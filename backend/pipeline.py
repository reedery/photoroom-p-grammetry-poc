import subprocess
from pathlib import Path
from typing import List, Optional
import requests

class PhotogrammetryPipeline:
    """Handles the complete photogrammetry pipeline"""
    
    def __init__(self, work_dir: Path, verbose: bool = True):
        self.work_dir = Path(work_dir)
        self.img_dir = self.work_dir / "images"
        self.masked_dir = self.work_dir / "masked"  # NEW: fo r background-removed images
        self.colmap_dir = self.work_dir / "colmap"
        self.output_dir = self.work_dir / "output"
        self.verbose = verbose
        
        # Create directories
        for d in [self.img_dir, self.masked_dir, self.colmap_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def log(self, message: str):
        """Print message if verbose mode is on"""
        if self.verbose:
            print(message)
    
    def save_images(self, image_data: List[bytes]) -> None:
        """Save uploaded images to disk"""
        self.log(f"Saving {len(image_data)} images...")
        
        for i, data in enumerate(image_data):
            img_path = self.img_dir / f"image_{i:03d}.jpg"
            img_path.write_bytes(data)
        
        self.log(f"✓ Saved {len(image_data)} images to {self.img_dir}")
    
    def run_feature_extraction(self) -> dict:
        """Run COLMAP feature extraction"""
        self.log("Running COLMAP feature extraction...")
        
        db_path = self.colmap_dir / "database.db"
        
        try:
            result = subprocess.run([
                "colmap", "feature_extractor",
                "--database_path", str(db_path),
                "--image_path", str(self.img_dir),
                "--ImageReader.single_camera", "1",
                "--ImageReader.camera_model", "SIMPLE_RADIAL"
            ], check=True, capture_output=True, text=True)
            
            self.log("✓ Feature extraction complete")
            
            # Log some COLMAP output if in verbose mode
            if self.verbose and result.stderr:
                for line in result.stderr.split('\n')[-5:]:  # Last 5 lines
                    if line.strip():
                        self.log(f"  {line}")
            
            return {
                "success": True,
                "database_path": str(db_path),
                "database_exists": db_path.exists(),
                "database_size": db_path.stat().st_size if db_path.exists() else 0
            }
            
        except subprocess.CalledProcessError as e:
            self.log(f"✗ Feature extraction failed")
            self.log(f"Error: {e.stderr}")
            return {
                "success": False,
                "error": e.stderr
            }
    
    def run_feature_matching(self) -> dict:
        """Run COLMAP feature matching"""
        self.log("Running COLMAP feature matching...")
        
        db_path = self.colmap_dir / "database.db"
        
        try:
            result = subprocess.run([
                "colmap", "exhaustive_matcher",
                "--database_path", str(db_path)
            ], check=True, capture_output=True, text=True)
            
            self.log("✓ Feature matching complete")
            
            if self.verbose and result.stderr:
                for line in result.stderr.split('\n')[-5:]:
                    if line.strip():
                        self.log(f"  {line}")
            
            return {
                "success": True
            }
            
        except subprocess.CalledProcessError as e:
            self.log(f"✗ Feature matching failed")
            self.log(f"Error: {e.stderr}")
            return {
                "success": False,
                "error": e.stderr
            }
    
    def run_mapper(self) -> dict:
        """Run COLMAP mapper (reconstruction)"""
        self.log("Running COLMAP mapper (this may take a minute)...")
        
        db_path = self.colmap_dir / "database.db"
        sparse_path = self.colmap_dir / "sparse"
        sparse_path.mkdir(exist_ok=True)
        
        try:
            result = subprocess.run([
                "colmap", "mapper",
                "--database_path", str(db_path),
                "--image_path", str(self.img_dir),
                "--output_path", str(sparse_path),
                # More permissive parameters for difficult cases
                "--Mapper.init_min_num_inliers", "50",  # Lower threshold (default 100)
                "--Mapper.abs_pose_min_num_inliers", "10",  # Lower threshold (default 30)
                "--Mapper.abs_pose_min_inlier_ratio", "0.15",  # Lower ratio (default 0.25)
                "--Mapper.init_max_error", "8",  # Higher error tolerance (default 4)
                "--Mapper.max_model_overlap", "3",  # Allow more model overlap
            ], check=True, capture_output=True, text=True)
            
            self.log("✓ Mapper complete")
            
            if self.verbose and result.stderr:
                for line in result.stderr.split('\n')[-10:]:  # Show more lines
                    if line.strip():
                        self.log(f"  {line}")
            
            # Check if reconstruction was created
            reconstruction_path = sparse_path / "0"
            reconstruction_exists = reconstruction_path.exists()
            
            # Count files in reconstruction
            reconstruction_files = []
            if reconstruction_exists:
                reconstruction_files = list(reconstruction_path.glob("*"))
            
            return {
                "success": reconstruction_exists,  # Only success if reconstruction exists
                "reconstruction_exists": reconstruction_exists,
                "reconstruction_path": str(reconstruction_path) if reconstruction_exists else None,
                "reconstruction_files": [f.name for f in reconstruction_files],
                "warning": "No reconstruction created" if not reconstruction_exists else None
            }
            
        except subprocess.CalledProcessError as e:
            self.log(f"✗ Mapper failed")
            self.log(f"Error: {e.stderr}")
            return {
                "success": False,
                "error": e.stderr
            }
    
    def run_colmap_sfm(self) -> dict:
        """Run complete COLMAP Structure from Motion pipeline"""
        self.log("\n" + "-"*50)
        self.log("COLMAP Structure from Motion Pipeline")
        self.log("-"*50 + "\n")
        
        # Step 1: Feature extraction
        extraction_result = self.run_feature_extraction()
        if not extraction_result["success"]:
            return {
                "success": False,
                "stage": "feature_extraction",
                "error": extraction_result.get("error")
            }
        
        # Step 2: Feature matching
        matching_result = self.run_feature_matching()
        if not matching_result["success"]:
            return {
                "success": False,
                "stage": "feature_matching",
                "error": matching_result.get("error")
            }
        
        # Step 3: Mapper (reconstruction)
        mapper_result = self.run_mapper()
        if not mapper_result["success"]:
            return {
                "success": False,
                "stage": "mapper",
                "error": mapper_result.get("error")
            }
        
        self.log("\n✓ Complete SfM pipeline finished successfully!\n")
        
        return {
            "success": True,
            "feature_extraction": extraction_result,
            "feature_matching": matching_result,
            "mapper": mapper_result
        }

    def remove_backgrounds(self, photoroom_api_key: str) -> dict:
        """Remove backgrounds using Photoroom API"""
        self.log("\nRemoving backgrounds with Photoroom API...")
        
        image_files = sorted(self.img_dir.glob("*.jpg"))
        
        if not image_files:
            return {
                "success": False,
                "error": "No images found to process"
            }
        
        processed = 0
        failed = 0
        
        for i, img_path in enumerate(image_files):
            self.log(f"  - Processing {img_path.name} ({i+1}/{len(image_files)})")
            
            try:
                with open(img_path, 'rb') as f:
                    response = requests.post(
                        'https://sdk.photoroom.com/v1/segment',
                        headers={'x-api-key': photoroom_api_key},
                        files={'image_file': f},
                        data={
                            'format': 'png',
                            'channels': 'rgba'
                        },
                        timeout=30
                    )
                
                if response.status_code == 200:
                    # Save as PNG with transparency
                    output_path = self.masked_dir / f"{img_path.stem}.png"
                    output_path.write_bytes(response.content)
                    processed += 1
                else:
                    self.log(f"    ✗ Failed: {response.status_code} - {response.text[:100]}")
                    failed += 1
                    
            except Exception as e:
                self.log(f"    ✗ Error: {str(e)}")
                failed += 1
        
        self.log(f"✓ Background removal complete: {processed} succeeded, {failed} failed\n")
        
        return {
            "success": failed == 0,
            "processed": processed,
            "failed": failed,
            "total": len(image_files)
        }
    
    def run_full_pipeline(self, image_data: List[bytes], photoroom_api_key: Optional[str] = None) -> dict:
        """Run the complete pipeline with optional background removal"""
        self.log("\n" + "="*50)
        self.log("Starting Full Photogrammetry Pipeline")
        self.log("="*50 + "\n")
        
        # Step 1: Save images
        self.save_images(image_data)
        
        # Step 2: Run SfM on original images
        self.log("\n--- PHASE 1: Structure from Motion (Original Images) ---\n")
        sfm_result = self.run_colmap_sfm()
        
        if not sfm_result["success"]:
            return {
                "success": False,
                "stage": "sfm",
                "error": sfm_result
            }
        
        # Step 3: Remove backgrounds (if API key provided)
        bg_removal_result = None
        if photoroom_api_key:
            self.log("\n--- PHASE 2: Background Removal ---\n")
            bg_removal_result = self.remove_backgrounds(photoroom_api_key)
        else:
            self.log("\n--- PHASE 2: Background Removal (SKIPPED - No API key) ---\n")
        
        # Count saved files
        saved_files = list(self.img_dir.glob("*.jpg"))
        masked_files = list(self.masked_dir.glob("*.png")) if photoroom_api_key else []
        
        self.log("\n" + "="*50)
        self.log("Full Pipeline Complete!")
        self.log("="*50 + "\n")
        
        return {
            "success": True,
            "images_saved": len(saved_files),
            "images_masked": len(masked_files),
            "work_directory": str(self.work_dir),
            "image_directory": str(self.img_dir),
            "masked_directory": str(self.masked_dir) if photoroom_api_key else None,
            "colmap_directory": str(self.colmap_dir),
            "output_directory": str(self.output_dir),
            "colmap_sfm": sfm_result,
            "background_removal": bg_removal_result
        }
