from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from background_removal import BackgroundRemover


class TripoSRPipeline:
    """Minimal pipeline: save images → optional BG removal → run TripoSR → return outputs."""

    def __init__(self, work_dir: Path, verbose: bool = True):
        self.work_dir = Path(work_dir)
        self.img_dir = self.work_dir / "images"
        self.masked_dir = self.work_dir / "masked"
        self.output_dir = self.work_dir / "triposr_output"
        self.verbose = verbose

        for d in [self.img_dir, self.masked_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def save_images(self, image_data: List[bytes]) -> List[Path]:
        import imghdr
        from PIL import Image
        import io
        
        self.log(f"Saving {len(image_data)} image(s)...")
        saved: List[Path] = []
        
        for i, data in enumerate(image_data):
            # Try to detect format
            kind = imghdr.what(None, h=data)
            
            # Check if it might be HEIC (imghdr doesn't detect HEIC)
            if kind is None and (data[:4] == b'ftyp' or data[4:12] == b'ftypheic' or data[4:12] == b'ftypheix'):
                # Convert HEIC to JPEG
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                    
                    img = Image.open(io.BytesIO(data))
                    img_path = self.img_dir / f"image_{i:03d}.jpg"
                    img.save(img_path, "JPEG", quality=95)
                    saved.append(img_path)
                    self.log(f"  Converted HEIC to JPEG: {img_path.name}")
                    continue
                except Exception as e:
                    self.log(f"  Warning: Could not convert HEIC: {e}")
                    kind = "jpeg"  # fallback
            
            # Handle standard formats
            ext = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}.get(kind or "jpeg", ".jpg")
            img_path = self.img_dir / f"image_{i:03d}{ext}"
            img_path.write_bytes(data)
            saved.append(img_path)
            
        self.log(f"✓ Saved {len(saved)} image(s) to {self.img_dir}")
        return saved

    def remove_backgrounds(self, api_key: Optional[str], image_paths: List[Path]) -> Tuple[List[Path], Optional[dict]]:
        # TEMP
        api_key = ""
        
        if not api_key:
            self.log("Background removal skipped (no API key).")
            return image_paths, None

        self.log("Removing backgrounds via Photoroom API...")
        remover = BackgroundRemover(self.img_dir, self.masked_dir, verbose=self.verbose)
        result = remover.remove_backgrounds(api_key, image_format="png")

        # Collect masked outputs; fall back to originals if none produced
        masked = sorted(self.masked_dir.glob("*.png"))
        if not masked:
            self.log("No masked images produced; falling back to original inputs.")
            return image_paths, result
        return masked, result

    def _find_triposr_entrypoint(self) -> Optional[Path]:
        """Best-effort search for TripoSR CLI within container or local environment."""
        # Allow override via env var, with local-friendly defaults
        default_paths = [
            "/root/TripoSR",  # Modal/container path
            str(Path(__file__).parent / "TripoSR"),  # Local backend directory
            str(Path.home() / "TripoSR"),  # User home directory
            "./TripoSR",  # Current directory
        ]
        
        base_path = os.environ.get("TRIPOSR_DIR", None)
        if base_path:
            bases = [Path(base_path).resolve()]
        else:
            # Check paths with permission error handling
            bases = []
            for p in default_paths:
                try:
                    path = Path(p)
                    if path.exists():
                        bases.append(path.resolve())
                except (PermissionError, OSError):
                    # Skip paths we don't have permission to access
                    continue
        
        for base in bases:
            candidates = [
                base / "run.py",
                base / "scripts" / "run.py",
                base / "inference" / "run.py",
            ]
            for c in candidates:
                if c.exists():
                    return c
        
        return None

    def run_triposr(self, input_images: List[Path]) -> dict:
        if not input_images:
            return {"success": False, "error": "No input images provided to TripoSR"}

        entry = self._find_triposr_entrypoint()
        if not entry:
            return {
                "success": False,
                "error": "TripoSR entrypoint not found. Ensure the repo is available in TRIPOSR_DIR or /root/TripoSR.",
            }

        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Try with texture baking first, but be prepared to fallback
        cmd = [
            "python",
            str(entry),
            *[str(p) for p in input_images],
            "--output-dir",
            str(self.output_dir),
            "--bake-texture",
            "--model-save-format",
            "glb",
        ]

        self.log("Running TripoSR (this uses GPU if available)...")
        try:
            # Set up environment for headless OpenGL rendering
            env = os.environ.copy()
            xvfb_proc = None
            
            # Try to use Xvfb if available, otherwise use EGL for headless rendering
            import shutil
            if shutil.which("Xvfb"):
                env["DISPLAY"] = ":99"
                try:
                    # Start Xvfb virtual display in background
                    xvfb_proc = subprocess.Popen(
                        ["Xvfb", ":99", "-screen", "0", "1024x768x24"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    # Give Xvfb time to start
                    import time
                    time.sleep(0.2)
                    self.log("Using Xvfb for headless rendering")
                except Exception as e:
                    self.log(f"Warning: Failed to start Xvfb: {e}")
                    xvfb_proc = None
            else:
                # Use EGL for headless rendering (no X server needed)
                env["PYOPENGL_PLATFORM"] = "egl"
                self.log("Using EGL for headless rendering (Xvfb not available)")
            
            try:
                self.log(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                )
            finally:
                # Clean up Xvfb if it was started
                if xvfb_proc:
                    xvfb_proc.terminate()
                    try:
                        xvfb_proc.wait(timeout=2)
                    except:
                        xvfb_proc.kill()
            
            # Always show full output for debugging
            if result.stdout:
                self.log("=== TripoSR STDOUT ===")
                self.log(result.stdout)
            if result.stderr:
                self.log("=== TripoSR STDERR ===")
                self.log(result.stderr)
        except subprocess.CalledProcessError as e:
            # Check if it's a device mismatch error during texture baking
            if "Expected all tensors to be on the same device" in str(e.stderr):
                self.log("Texture baking failed due to device mismatch. Retrying without texture baking...")
                
                # Try again without texture baking
                cmd_no_texture = [
                    "python",
                    str(entry),
                    *[str(p) for p in input_images],
                    "--output-dir",
                    str(self.output_dir),
                    "--model-save-format",
                    "glb",
                ]
                
                try:
                    self.log(f"Retrying with command: {' '.join(cmd_no_texture)}")
                    result = subprocess.run(
                        cmd_no_texture,
                        check=True,
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    
                    # Show output from successful retry
                    if result.stdout:
                        self.log("=== TripoSR Retry STDOUT ===")
                        self.log(result.stdout)
                    if result.stderr:
                        self.log("=== TripoSR Retry STDERR ===")
                        self.log(result.stderr)
                        
                except subprocess.CalledProcessError as retry_e:
                    error_msg = f"TripoSR failed with exit code {retry_e.returncode} (retry without texture baking)"
                    if retry_e.stdout:
                        error_msg += f"\nSTDOUT: {retry_e.stdout}"
                    if retry_e.stderr:
                        error_msg += f"\nSTDERR: {retry_e.stderr}"
                    self.log(f"TripoSR Retry Error: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"TripoSR failed with exit code {e.returncode}"
                if e.stdout:
                    error_msg += f"\nSTDOUT: {e.stdout}"
                if e.stderr:
                    error_msg += f"\nSTDERR: {e.stderr}"
                self.log(f"TripoSR Error: {error_msg}")
                return {"success": False, "error": error_msg}

        # Collect outputs (GLB format with baked textures)
        produced = sorted(self.output_dir.glob("**/*"))
        files = [str(p) for p in produced if p.is_file()]
        
        self.log(f"TripoSR completed. Found {len(files)} output files:")
        for f in files:
            self.log(f"  - {f}")
        
        return {
            "success": True,
            "output_dir": str(self.output_dir),
            "files": files,
        }

    def run(self, image_data: List[bytes], photoroom_api_key: Optional[str] = None) -> dict:
        # Input cap: up to 5 images as requested
        if len(image_data) == 0:
            return {"success": False, "error": "No images provided"}
        if len(image_data) > 5:
            image_data = image_data[:5]

        saved = self.save_images(image_data)
        masked, bg_result = self.remove_backgrounds(photoroom_api_key, saved)

        triposr_result = self.run_triposr(masked)

        return {
            "success": triposr_result.get("success", False),
            "work_directory": str(self.work_dir),
            "image_directory": str(self.img_dir),
            "masked_directory": str(self.masked_dir) if masked != saved else None,
            "output_directory": str(self.output_dir),
            "background_removal": bg_result,
            "triposr": triposr_result,
        }


