"""
Background removal module using Photoroom API
Handles all background removal operations with robust error handling and retries
"""

import time
import tempfile
from pathlib import Path
from typing import Optional, Callable
import requests


class BackgroundRemover:
    """Handles background removal using Photoroom API with robust error handling"""
    
    def __init__(self, api_key: str, verbose: bool = True, output_type: str = 'mask'):
        """
        Args:
            api_key: Photoroom API key
            verbose: Enable verbose logging
            output_type: 'mask' for binary masks (alpha channel only), 
                        'rgba' for transparent images with RGBA
        """
        self.api_key = api_key
        self.verbose = verbose
        self.output_type = output_type  # 'mask' or 'rgba'
        self.api_url = 'https://sdk.photoroom.com/v1/segment'
        
    def log(self, message: str):
        """Print message if verbose mode is on"""
        if self.verbose:
            print(message, flush=True)
    
    def remove_background_single(
        self, 
        input_path: Path, 
        output_path: Path,
        max_retries: int = 3,
        timeout: int = 90
    ) -> bool:
        """
        Remove background from a single image with retry logic
        
        Args:
            input_path: Path to input image
            output_path: Path to save output PNG
            max_retries: Number of retry attempts
            timeout: Timeout in seconds per request
            
        Returns:
            True if successful, False otherwise
        """
        retry_count = 0
        
        # Create session for this image (fresh connection)
        session = requests.Session()
        session.headers.update({'x-api-key': self.api_key})
        
        try:
            while retry_count < max_retries:
                try:
                    # Use a temporary file to ensure atomic writes
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as tmp_file:
                        tmp_path = Path(tmp_file.name)
                    
                    try:
                        # Read and send the image
                        with open(input_path, 'rb') as f:
                            image_data = f.read()
                        
                        # Determine channels based on output type
                        channels = 'alpha' if self.output_type == 'mask' else 'rgba'
                        
                        response = session.post(
                            self.api_url,
                            files={'image_file': (input_path.name, image_data, 'image/jpeg')},
                            data={
                                'format': 'png',
                                'channels': channels  # 'alpha' for masks, 'rgba' for transparent images
                            },
                            timeout=timeout,
                            stream=False  # Don't stream to avoid partial downloads
                        )
                        
                        # Handle response
                        if response.status_code == 200:
                            # Write to temp file first
                            tmp_path.write_bytes(response.content)
                            
                            # Verify the file was written correctly
                            if tmp_path.stat().st_size > 0:
                                # Atomic move to final location
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                tmp_path.replace(output_path)
                                self.log(f"    ✓ Success ({output_path.stat().st_size:,} bytes)")
                                return True
                            else:
                                self.log(f"    ⚠️  Empty response, retrying...")
                                retry_count += 1
                                
                        elif response.status_code == 429:  # Rate limit
                            wait_time = 2 ** (retry_count + 1)  # Exponential backoff
                            self.log(f"    ⚠️  Rate limited, waiting {wait_time}s...")
                            time.sleep(wait_time)
                            retry_count += 1
                            
                        elif response.status_code >= 500:  # Server error
                            self.log(f"    ⚠️  Server error {response.status_code}, retrying...")
                            retry_count += 1
                            time.sleep(2)
                            
                        else:
                            # Client error - don't retry
                            self.log(f"    ✗ Failed: {response.status_code} - {response.text[:100]}")
                            return False
                            
                    finally:
                        # Clean up temp file if it still exists
                        if tmp_path.exists():
                            try:
                                tmp_path.unlink()
                            except:
                                pass
                                
                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.log(f"    ⚠️  Timeout, retrying ({retry_count}/{max_retries})...")
                        time.sleep(2)
                    else:
                        self.log(f"    ✗ Failed after {max_retries} retries: Timeout")
                        return False
                        
                except requests.exceptions.ConnectionError as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.log(f"    ⚠️  Connection error, retrying ({retry_count}/{max_retries})...")
                        time.sleep(3)
                    else:
                        self.log(f"    ✗ Failed after {max_retries} retries: Connection error")
                        return False
                        
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.log(f"    ⚠️  Error: {str(e)[:100]}, retrying ({retry_count}/{max_retries})...")
                        time.sleep(2)
                    else:
                        self.log(f"    ✗ Failed after {max_retries} retries: {str(e)[:100]}")
                        return False
                        
        finally:
            # Always close the session
            try:
                session.close()
            except:
                pass
        
        return False
    
    def process_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        file_pattern: str = "*.jpg",
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """
        Process all images in a directory
        
        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save output images
            file_pattern: Glob pattern for input files
            progress_callback: Optional callback(current, total, filename)
            
        Returns:
            dict with processing statistics
        """
        if self.output_type == 'mask':
            self.log("\nGenerating binary masks with Photoroom API...")
        else:
            self.log("\nRemoving backgrounds with Photoroom API...")
        
        image_files = sorted(input_dir.glob(file_pattern))
        
        if not image_files:
            return {
                "success": False,
                "error": "No images found to process",
                "processed": 0,
                "failed": 0,
                "total": 0
            }
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        processed = 0
        failed = 0
        
        for i, img_path in enumerate(image_files, 1):
            self.log(f"  - Processing {img_path.name} ({i}/{len(image_files)})")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i, len(image_files), img_path.name)
            
            output_path = output_dir / f"{img_path.stem}.png"
            
            if self.remove_background_single(img_path, output_path):
                processed += 1
            else:
                failed += 1
        
        if self.output_type == 'mask':
            self.log(f"✓ Binary mask generation complete: {processed} succeeded, {failed} failed\n")
        else:
            self.log(f"✓ Background removal complete: {processed} succeeded, {failed} failed\n")
        
        # Consider it successful if we processed at least some images
        return {
            "success": processed > 0,
            "processed": processed,
            "failed": failed,
            "total": len(image_files),
            "partial_success": processed > 0 and failed > 0
        }

