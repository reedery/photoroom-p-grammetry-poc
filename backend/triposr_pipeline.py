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

        self.log(f"Saving {len(image_data)} image(s)...")
        saved: List[Path] = []
        for i, data in enumerate(image_data):
            kind = imghdr.what(None, h=data) or "jpeg"
            ext = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}.get(kind, ".jpg")
            img_path = self.img_dir / f"image_{i:03d}{ext}"
            img_path.write_bytes(data)
            saved.append(img_path)
        self.log(f"✓ Saved {len(saved)} image(s) to {self.img_dir}")
        return saved

    def remove_backgrounds(self, api_key: Optional[str], image_paths: List[Path]) -> Tuple[List[Path], Optional[dict]]:
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
        # Allow override via env var
        base = Path(os.environ.get("TRIPOSR_DIR", "/root/TripoSR")).resolve()
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
        cmd = [
            "python",
            str(entry),
            *[str(p) for p in input_images],
            "--output-dir",
            str(self.output_dir),
            # Skip texture baking for now due to CPU/GPU device mismatch in TripoSR
            # The mesh (.obj) will still be generated successfully
            # "--bake-texture",
        ]

        self.log("Running TripoSR (this uses GPU if available)...")
        try:
            # Set up environment for headless OpenGL rendering
            env = os.environ.copy()
            env["DISPLAY"] = ":99"
            
            # Start Xvfb virtual display in background
            xvfb_proc = subprocess.Popen(
                ["Xvfb", ":99", "-screen", "0", "1024x768x24"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            try:
                # Give Xvfb time to start (reduced from 0.5s to 0.2s)
                import time
                time.sleep(0.2)
                
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                )
            finally:
                # Clean up Xvfb
                xvfb_proc.terminate()
                xvfb_proc.wait(timeout=2)
            if self.verbose:
                # Truncate logs to last lines
                tail = "\n".join(result.stdout.splitlines()[-20:])
                if tail.strip():
                    self.log(tail)
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr or str(e)}

        # Collect outputs (common outputs: .obj/.mtl/.png or .glb)
        produced = sorted(self.output_dir.glob("**/*"))
        files = [str(p) for p in produced if p.is_file()]
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


