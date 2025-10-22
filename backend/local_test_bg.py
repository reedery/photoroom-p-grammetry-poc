"""
Local testing script for background removal only
Tests the Photoroom API integration and mask generation
"""

from pathlib import Path
from bg_removal import BackgroundRemover
import os
import sys


def test_background_removal():
    """Test background removal on a local image folder"""
    
    # Setup paths
    img_folder = Path(__file__).parent / "img_testing3"  # Smaller folder for quick testing
    output_folder = Path(__file__).parent / "bg_test_output"
    
    # Clean up previous test
    if output_folder.exists():
        import shutil
        shutil.rmtree(output_folder)
    
    output_folder.mkdir(exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"BACKGROUND REMOVAL TEST")
    print(f"{'='*60}\n")
    
    # Check for images
    test_images = list(img_folder.glob("*.jpg"))
    
    if not test_images:
        print(f"❌ No images found in {img_folder.name}/")
        print(f"   Looking in: {img_folder.absolute()}")
        return
    
    print(f"Found {len(test_images)} test images in {img_folder.name}/:")
    for img in sorted(test_images):
        print(f"  - {img.name} ({img.stat().st_size:,} bytes)")
    
    # Get API key from environment or use hardcoded (for testing)
    api_key = os.environ.get("PHOTOROOM_API_KEY")
    
    if not api_key:
        print(f"\n no api key")
    
    print(f"✓ Using API key: {api_key[:20]}...{api_key[-10:]}")
    print(f"  (key length: {len(api_key)} characters)")
    
    # Create background remover
    # output_type='mask' generates binary masks (alpha channel only)
    # output_type='rgba' generates transparent images with RGBA
    bg_remover = BackgroundRemover(
        api_key=api_key,
        verbose=True,
        output_type='mask'  # Change to 'rgba' if you want full transparent images
    )
    
    # Process the directory
    print(f"\nOutput folder: {output_folder.absolute()}\n")
    
    result = bg_remover.process_directory(
        input_dir=img_folder,
        output_dir=output_folder,
        file_pattern="*.jpg"
    )
    
    # Print results
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}\n")
    
    print(f"Total images:    {result['total']}")
    print(f"Processed:       {result['processed']}")
    print(f"Failed:          {result['failed']}")
    print(f"Success:         {result['success']}")
    
    if result.get('partial_success'):
        print(f"\n⚠️  Partial success - some images failed")
    
    if result['success']:
        print(f"\n✅ Background removal test completed!")
        print(f"\nMasks saved to: {output_folder.absolute()}")
        print(f"\nYou can now inspect the generated masks.")
    else:
        print(f"\n❌ Background removal test failed")
        if result.get('error'):
            print(f"   Error: {result['error']}")
    
    print()
    return result


if __name__ == "__main__":
    # You can override the API key via command line for testing
    if len(sys.argv) > 1:
        os.environ["PHOTOROOM_API_KEY"] = sys.argv[1]
        print(f"✓ Using API key from command line argument\n")
    
    test_background_removal()

