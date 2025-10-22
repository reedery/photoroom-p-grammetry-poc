from pathlib import Path
from typing import Optional
import requests


class BackgroundRemover:
    """Handles background removal using Photoroom API"""
    
    def __init__(self, input_dir: Path, output_dir: Path, verbose: bool = True):
        """
        Initialize the background remover
        
        Args:
            input_dir: Directory containing images to process
            output_dir: Directory where processed images will be saved
            verbose: Whether to print progress messages
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str):
        """Print message if verbose mode is on"""
        if self.verbose:
            print(message)
    
    def remove_backgrounds(self, photoroom_api_key: str, image_format: str = "png") -> dict:
        """
        Remove backgrounds from all images in input directory using Photoroom API
        
        Args:
            photoroom_api_key: Photoroom API key for authentication
            image_format: Output format ('png' or 'jpg')
        
        Returns:
            dict: Results containing success status, processed count, failed count, and total
        """
        self.log("\nRemoving backgrounds with Photoroom API...")
        
        # Find all images in input directory
        image_files = sorted(self.input_dir.glob("*.jpg"))
        image_files.extend(sorted(self.input_dir.glob("*.jpeg")))
        image_files.extend(sorted(self.input_dir.glob("*.png")))
        
        if not image_files:
            return {
                "success": False,
                "error": "No images found to process",
                "processed": 0,
                "failed": 0,
                "total": 0
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
                            'format': image_format,
                            'channels': 'rgba'
                        },
                        timeout=30
                    )
                
                if response.status_code == 200:
                    # Save with appropriate extension
                    output_extension = '.png' if image_format == 'png' else '.jpg'
                    output_path = self.output_dir / f"{img_path.stem}{output_extension}"
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
    
    def remove_background_single(self, image_path: Path, photoroom_api_key: str, 
                                 output_path: Optional[Path] = None, 
                                 image_format: str = "png") -> dict:
        """
        Remove background from a single image
        
        Args:
            image_path: Path to the image to process
            photoroom_api_key: Photoroom API key for authentication
            output_path: Optional custom output path (defaults to output_dir)
            image_format: Output format ('png' or 'jpg')
        
        Returns:
            dict: Results containing success status and output path
        """
        self.log(f"Processing single image: {image_path.name}")
        
        try:
            with open(image_path, 'rb') as f:
                response = requests.post(
                    'https://sdk.photoroom.com/v1/segment',
                    headers={'x-api-key': photoroom_api_key},
                    files={'image_file': f},
                    data={
                        'format': image_format,
                        'channels': 'rgba'
                    },
                    timeout=30
                )
            
            if response.status_code == 200:
                # Determine output path
                if output_path is None:
                    output_extension = '.png' if image_format == 'png' else '.jpg'
                    output_path = self.output_dir / f"{image_path.stem}{output_extension}"
                
                output_path.write_bytes(response.content)
                self.log(f"✓ Saved to {output_path}")
                
                return {
                    "success": True,
                    "output_path": str(output_path)
                }
            else:
                error_msg = f"API error: {response.status_code} - {response.text[:100]}"
                self.log(f"✗ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            self.log(f"✗ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

