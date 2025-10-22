import subprocess
from pathlib import Path
from typing import List, Optional
import numpy as np
import open3d as o3d
from bg_removal import BackgroundRemover

class PhotogrammetryPipeline:
    """Handles the complete photogrammetry pipeline"""
    
    def __init__(self, work_dir: Path, verbose: bool = True, cpu_only: bool = True):
        self.work_dir = Path(work_dir)
        self.img_dir = self.work_dir / "images"
        self.masked_dir = self.work_dir / "masked"  # Transparent PNGs from Photoroom
        self.masks_dir = self.work_dir / "masks"   # Binary masks for COLMAP
        self.colmap_dir = self.work_dir / "colmap"
        self.dense_dir = self.work_dir / "dense"   
        self.output_dir = self.work_dir / "output"
        self.verbose = verbose
        self.cpu_only = cpu_only  # Skip GPU-requiring steps
        
        # Create directories
        for d in [self.img_dir, self.masked_dir, self.masks_dir, self.colmap_dir, self.dense_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def log(self, message: str):
        """Print message if verbose mode is on"""
        if self.verbose:
            print(message, flush=True)  # Flush to ensure logs are sent immediately
    
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
        
        # Build command with GPU support if not in CPU-only mode
        cmd = [
            "colmap", "feature_extractor",
            "--database_path", str(db_path),
            "--image_path", str(self.img_dir),
            "--ImageReader.single_camera", "1",
            "--ImageReader.camera_model", "SIMPLE_RADIAL"
        ]
        
        # Enable GPU acceleration if available
        if not self.cpu_only:
            cmd.extend([
                "--SiftExtraction.use_gpu", "1",
                "--SiftExtraction.gpu_index", "0"
            ])
            self.log("   Using GPU acceleration for feature extraction")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
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
        
        # Build command with GPU support if not in CPU-only mode
        cmd = [
            "colmap", "exhaustive_matcher",
            "--database_path", str(db_path)
        ]
        
        # Enable GPU acceleration if available
        if not self.cpu_only:
            cmd.extend([
                "--SiftMatching.use_gpu", "1",
                "--SiftMatching.gpu_index", "0"
            ])
            self.log("   Using GPU acceleration for feature matching")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
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

    def generate_masks(self, photoroom_api_key: str) -> dict:
        """Generate binary masks directly from Photoroom API
        
        Uses Photoroom's 'alpha' channel mode to get grayscale masks directly,
        which is faster and more efficient than downloading RGBA and extracting alpha.
        """
        bg_remover = BackgroundRemover(
            api_key=photoroom_api_key, 
            verbose=self.verbose,
            output_type='mask'  # Get binary masks directly (alpha channel only)
        )
        return bg_remover.process_directory(
            input_dir=self.img_dir,
            output_dir=self.masks_dir,  # Save directly to masks directory
            file_pattern="*.jpg"
        )
    
    def export_sparse_point_cloud(self) -> dict:
        """Export sparse point cloud from COLMAP to PLY format"""
        self.log("\n" + "-"*50)
        self.log("Exporting Sparse Point Cloud")
        self.log("-"*50 + "\n")
        
        sparse_path = self.colmap_dir / "sparse" / "0"
        output_path = self.output_dir / "sparse.ply"
        
        try:
            result = subprocess.run([
                "colmap", "model_converter",
                "--input_path", str(sparse_path),
                "--output_path", str(output_path),
                "--output_type", "PLY"
            ], check=True, capture_output=True, text=True)
            
            point_cloud_size = output_path.stat().st_size if output_path.exists() else 0
            self.log(f"✓ Sparse point cloud exported to: {output_path}")
            self.log(f"   Size: {point_cloud_size:,} bytes\n")
            
            return {
                "success": True,
                "point_cloud_path": str(output_path),
                "point_cloud_size": point_cloud_size
            }
            
        except subprocess.CalledProcessError as e:
            self.log(f"✗ Failed to export sparse point cloud")
            self.log(f"Error: {e.stderr[:500]}")
            return {
                "success": False,
                "error": e.stderr
            }
    
    def run_colmap_mvs(self, use_masks: bool = True) -> dict:
        """Run COLMAP Multi-View Stereo for dense reconstruction (requires CUDA/GPU)
        
        Args:
            use_masks: If True, use binary masks to exclude background during reconstruction
        """
        self.log("\n" + "-"*50)
        self.log("COLMAP Multi-View Stereo (Dense Reconstruction)")
        self.log("-"*50 + "\n")
        
        sparse_path = self.colmap_dir / "sparse" / "0"
        
        # ALWAYS use original images for MVS (not the transparent PNGs)
        image_path = self.img_dir
        
        # Check if we have binary masks to use
        has_masks = use_masks and list(self.masks_dir.glob("*.png"))
        
        if has_masks:
            self.log("Using original images WITH binary masks (backgrounds will be excluded)")
        else:
            self.log("Using original images WITHOUT masks")
        
        try:
            # Step 1: Image undistortion
            self.log("\n1. Undistorting images...")
            result = subprocess.run([
                "colmap", "image_undistorter",
                "--image_path", str(image_path),
                "--input_path", str(sparse_path),
                "--output_path", str(self.dense_dir),
                "--output_type", "COLMAP"
            ], check=True, capture_output=True, text=True)
            
            self.log("   ✓ Image undistortion complete")
            
            # Step 2: Copy masks to dense directory if we have them
            # COLMAP expects masks in dense/images/ with same names as images
            if has_masks:
                self.log("\n2a. Setting up masks for patch match stereo...")
                dense_images_dir = self.dense_dir / "images"
                dense_masks_dir = self.dense_dir / "stereo" / "masks"
                dense_masks_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy masks to the location COLMAP expects
                import shutil
                for mask_file in self.masks_dir.glob("*.png"):
                    dest = dense_masks_dir / mask_file.name
                    shutil.copy(mask_file, dest)
                self.log(f"   ✓ Copied {len(list(self.masks_dir.glob('*.png')))} masks")
            
            # Step 2b: Patch match stereo (the slow part - REQUIRES CUDA)
            self.log(f"\n2{'b' if has_masks else ''}. Running patch match stereo (this can take several minutes)...")
            
            patch_cmd = [
                "colmap", "patch_match_stereo",
                "--workspace_path", str(self.dense_dir),
                "--PatchMatchStereo.geom_consistency", "true"
            ]
            
            # Enable mask filtering if we have masks
            if has_masks:
                patch_cmd.extend([
                    "--PatchMatchStereo.filter", "true",
                    "--PatchMatchStereo.filter_min_num_consistent", "2"
                ])
                self.log("   Using masks to filter background pixels")
            
            result = subprocess.run(patch_cmd, check=True, capture_output=True, text=True)
            
            self.log("   ✓ Patch match stereo complete")
            
            # Step 3: Stereo fusion
            self.log("\n3. Fusing depth maps...")
            fused_path = self.dense_dir / "fused.ply"
            result = subprocess.run([
                "colmap", "stereo_fusion",
                "--workspace_path", str(self.dense_dir),
                "--output_path", str(fused_path)
            ], check=True, capture_output=True, text=True)
            
            self.log("   ✓ Stereo fusion complete")
            
            # Check if point cloud was created and is valid
            point_cloud_exists = fused_path.exists()
            point_cloud_size = fused_path.stat().st_size if point_cloud_exists else 0
            
            # Verify the point cloud has actual data
            is_valid = False
            num_points = 0
            if point_cloud_exists and point_cloud_size > 1000:  # At least 1KB
                try:
                    import open3d as o3d
                    test_pcd = o3d.io.read_point_cloud(str(fused_path))
                    num_points = len(test_pcd.points)
                    is_valid = num_points > 100  # At least 100 points
                    
                    if is_valid:
                        self.log(f"\n✓ Dense reconstruction complete!")
                        self.log(f"   Point cloud: {fused_path}")
                        self.log(f"   Points: {num_points:,}")
                        self.log(f"   Size: {point_cloud_size:,} bytes")
                        if has_masks:
                            self.log(f"   Used binary masks: Yes\n")
                        else:
                            self.log(f"   Used binary masks: No\n")
                    else:
                        self.log(f"\n✗ Dense reconstruction produced empty point cloud ({num_points} points)")
                        self.log(f"   This means MVS failed - check CUDA availability and image quality\n")
                except Exception as e:
                    self.log(f"\n✗ Could not read point cloud: {str(e)}\n")
            else:
                self.log(f"\n✗ Dense reconstruction produced invalid file (size: {point_cloud_size} bytes)\n")
            
            return {
                "success": is_valid,
                "point_cloud_path": str(fused_path) if is_valid else None,
                "point_cloud_size": point_cloud_size,
                "used_masks": has_masks,
                "num_points": num_points,
                "type": "dense",
                "error": "Empty or invalid point cloud - MVS failed" if not is_valid else None
            }
            
        except subprocess.CalledProcessError as e:
            # Check if it's a CUDA error
            error_msg = e.stderr if e.stderr else str(e)
            if "CUDA" in error_msg or "cuda" in error_msg:
                self.log(f"⚠️  Dense reconstruction requires CUDA/GPU (not available)")
                self.log(f"   Falling back to sparse point cloud...\n")
                return {
                    "success": False,
                    "error": "CUDA not available",
                    "cuda_required": True
                }
            else:
                self.log(f"✗ MVS failed at a subprocess step")
                self.log(f"Error: {error_msg[:500]}")
                return {
                    "success": False,
                    "error": error_msg
                }
    
    def generate_mesh(self, point_cloud_path: Optional[str] = None, is_sparse: bool = False) -> dict:
        """Generate mesh from point cloud using Open3D"""
        self.log("\n" + "-"*50)
        self.log("Mesh Generation with Open3D")
        self.log("-"*50 + "\n")
        
        # Use provided path or default to dense point cloud
        if point_cloud_path:
            pcd_path = Path(point_cloud_path)
        else:
            pcd_path = self.dense_dir / "fused.ply"
        
        if not pcd_path.exists():
            return {
                "success": False,
                "error": f"Point cloud file not found: {pcd_path}"
            }
        
        cloud_type = "sparse" if is_sparse else "dense"
        self.log(f"Using {cloud_type} point cloud: {pcd_path.name}")
        
        try:
            # Step 1: Load point cloud
            self.log("\n1. Loading point cloud...")
            pcd = o3d.io.read_point_cloud(str(pcd_path))
            num_points = len(pcd.points)
            has_colors = pcd.has_colors()
            self.log(f"   ✓ Loaded {num_points:,} points ({cloud_type})")
            if has_colors:
                self.log(f"   ✓ Point cloud has color information")
            else:
                self.log(f"   ⚠️  Point cloud has no color information")
            
            if num_points == 0:
                return {
                    "success": False,
                    "error": "Point cloud is empty"
                }
            
            # Step 2: Estimate normals
            self.log("\n2. Estimating normals...")
            pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(
                    radius=0.1, max_nn=30
                )
            )
            # Orient normals consistently
            pcd.orient_normals_consistent_tangent_plane(30)
            self.log("   ✓ Normals estimated")
            
            # Step 3: Poisson reconstruction
            self.log("\n3. Running Poisson surface reconstruction...")
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                pcd, depth=9
            )
            self.log(f"   ✓ Initial mesh: {len(mesh.vertices):,} vertices, {len(mesh.triangles):,} triangles")
            
            # Step 4: Remove low-density vertices (cleanup)
            self.log("\n4. Cleaning mesh...")
            densities = np.asarray(densities)
            vertices_to_remove = densities < np.quantile(densities, 0.01)
            mesh.remove_vertices_by_mask(vertices_to_remove)
            self.log(f"   ✓ After cleanup: {len(mesh.vertices):,} vertices, {len(mesh.triangles):,} triangles")
            
            # Step 5: Transfer colors from point cloud to mesh
            if has_colors:
                self.log("\n5. Transferring vertex colors from point cloud...")
                # Paint mesh vertices by finding nearest colored points
                mesh.paint_uniform_color([0.5, 0.5, 0.5])  # Default gray
                mesh_vertices = np.asarray(mesh.vertices)
                pcd_tree = o3d.geometry.KDTreeFlann(pcd)
                
                vertex_colors = np.zeros((len(mesh_vertices), 3))
                for i, vertex in enumerate(mesh_vertices):
                    # Find nearest point in colored point cloud
                    [_, idx, _] = pcd_tree.search_knn_vector_3d(vertex, 1)
                    if len(idx) > 0:
                        vertex_colors[i] = np.asarray(pcd.colors)[idx[0]]
                
                mesh.vertex_colors = o3d.utility.Vector3dVector(vertex_colors)
                self.log(f"   ✓ Vertex colors transferred")
            else:
                self.log("\n5. Coloring mesh (uniform gray - no source colors)...")
                mesh.paint_uniform_color([0.7, 0.7, 0.7])
            
            # Step 6: Simplify mesh
            self.log("\n6. Simplifying mesh...")
            target_triangles = min(100000, len(mesh.triangles))
            mesh = mesh.simplify_quadric_decimation(
                target_number_of_triangles=target_triangles
            )
            self.log(f"   ✓ Final mesh: {len(mesh.vertices):,} vertices, {len(mesh.triangles):,} triangles")
            
            # Step 7: Save mesh with colors
            self.log("\n7. Saving mesh...")
            output_path = self.output_dir / "model.obj"
            # Write mesh with vertex colors
            o3d.io.write_triangle_mesh(
                str(output_path), 
                mesh,
                write_vertex_colors=has_colors
            )
            self.log(f"   ✓ Mesh saved to: {output_path}")
            if has_colors:
                self.log(f"   ✓ Vertex colors included\n")
            else:
                self.log(f"   (No vertex colors - using uniform color)\n")
            
            return {
                "success": True,
                "mesh_path": str(output_path),
                "mesh_size": output_path.stat().st_size,
                "vertices": len(mesh.vertices),
                "triangles": len(mesh.triangles),
                "point_cloud_points": num_points,
                "point_cloud_type": cloud_type,
                "has_vertex_colors": has_colors
            }
            
        except Exception as e:
            self.log(f"✗ Mesh generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_full_pipeline(self, image_data: List[bytes], photoroom_api_key: Optional[str] = None, pre_generated_masks: Optional[List[bytes]] = None) -> dict:
        """Run the complete pipeline: SfM -> Binary Masks -> Dense Reconstruction -> Mesh
        
        CPU-only mode skips MVS and uses sparse point cloud instead.
        Binary masks can be provided directly or generated from Photoroom API using 'alpha' channel mode.
        
        Args:
            image_data: List of image bytes
            photoroom_api_key: Optional Photoroom API key (generates masks if no pre_generated_masks)
            pre_generated_masks: Optional pre-generated mask bytes (skips API call)
        """
        self.log("\n" + "="*60)
        self.log("COMPLETE PHOTOGRAMMETRY PIPELINE")
        if self.cpu_only:
            self.log("(CPU-Only Mode - Using Sparse Reconstruction)")
        self.log("="*60 + "\n")
        
        # PHASE 1: Save images
        self.log("📸 PHASE 1: Saving Images")
        self.save_images(image_data)
        
        # PHASE 2: Structure from Motion (sparse reconstruction)
        self.log("\n🎯 PHASE 2: Structure from Motion (Sparse)")
        sfm_result = self.run_colmap_sfm()
        
        if not sfm_result["success"]:
            return {
                "success": False,
                "stage": "sfm",
                "error": sfm_result
            }
        
        # PHASE 3: Binary Mask Setup (optional)
        mask_result = None
        use_masks = False
        
        if pre_generated_masks:
            # Use provided masks directly
            self.log("\n🎨 PHASE 3: Binary Masks (Pre-generated)")
            self.log(f"   Saving {len(pre_generated_masks)} pre-generated masks...")
            
            # Save masks to masks directory
            for i, mask_data in enumerate(pre_generated_masks):
                mask_path = self.masks_dir / f"image_{i:03d}.png"
                mask_path.write_bytes(mask_data)
            
            self.log(f"✓ Saved {len(pre_generated_masks)} masks\n")
            use_masks = True
            mask_result = {
                "success": True,
                "processed": len(pre_generated_masks),
                "source": "pre_generated"
            }
            
        elif photoroom_api_key:
            # Generate binary masks from Photoroom API
            self.log("\n🎨 PHASE 3: Binary Mask Generation (Photoroom API)")
            
            mask_result = self.generate_masks(photoroom_api_key)
            use_masks = mask_result.get("success", False)
            
            if not use_masks:
                self.log("  ⚠️  Mask generation failed, continuing without masks")
        else:
            self.log("\n⏭️  PHASE 3: Binary Masks (SKIPPED - No API key or pre-generated masks)")
        
        # PHASE 4: Dense Reconstruction
        if self.cpu_only:
            # CPU-only mode: Export sparse point cloud
            self.log("\n⏭️  PHASE 4: Dense Reconstruction (SKIPPED - CPU-only mode)")
            self.log("   Dense reconstruction requires GPU/CUDA")
            self.log("   Exporting sparse point cloud instead...")
            
            sparse_result = self.export_sparse_point_cloud()
            if not sparse_result["success"]:
                return {
                    "success": False,
                    "stage": "sparse_export",
                    "error": sparse_result
                }
            point_cloud_path = sparse_result["point_cloud_path"]
            mvs_result = sparse_result
            is_sparse = True
        else:
            # GPU mode: Run dense reconstruction with masks
            self.log("\n🌟 PHASE 4: Dense Reconstruction (MVS)")
            mvs_result = self.run_colmap_mvs(use_masks=use_masks)
            
            if not mvs_result["success"]:
                # MVS failed - don't fallback, just fail
                return {
                    "success": False,
                    "stage": "mvs",
                    "error": mvs_result.get("error", "Dense reconstruction failed")
                }
            
            point_cloud_path = mvs_result.get("point_cloud_path")
            is_sparse = False
        
        # PHASE 5: Mesh Generation
        self.log("\n🎭 PHASE 5: Mesh Generation")
        mesh_result = self.generate_mesh(point_cloud_path=point_cloud_path, is_sparse=is_sparse)
        
        if not mesh_result["success"]:
            return {
                "success": False,
                "stage": "mesh_generation",
                "error": mesh_result
            }
        
        self.log("\n" + "="*60)
        self.log("✅ COMPLETE PIPELINE FINISHED SUCCESSFULLY!")
        self.log("="*60 + "\n")
        
        return {
            "success": True,
            "cpu_only_mode": self.cpu_only,
            "images_saved": len(list(self.img_dir.glob("*.jpg"))),
            "binary_masks": len(list(self.masks_dir.glob("*.png"))),
            "work_directory": str(self.work_dir),
            "output_mesh_path": mesh_result.get("mesh_path"),
            "colmap_sfm": sfm_result,
            "mask_generation": mask_result,
            "dense_reconstruction": mvs_result,
            "mesh_generation": mesh_result
        }
