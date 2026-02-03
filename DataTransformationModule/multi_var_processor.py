import os
import glob
import re
import numpy as np
import json
from skimage import measure
try:
    from .volume_loader import load_volume_from_ini
    from .extract_isosurface import save_obj, natural_sort_key
    from .calculate_trajectory import calculate_centroid, extract_time_index
except ImportError:
    from volume_loader import load_volume_from_ini
    from extract_isosurface import save_obj, natural_sort_key
    from calculate_trajectory import calculate_centroid, extract_time_index

class WaterMassProcessor:
    def __init__(self, data_root):
        self.data_root = data_root
        # Structure: { 'variable_name': { time_index: 'file_path' } }
        self.data_sources = {} 
        self.available_times = set()

    def register_variable(self, var_name, filename_pattern):
        """
        Register a data variable.
        var_name: e.g., 'temp', 'salt', 'oxygen'
        filename_pattern: e.g., 'volume_temperature_*.raw.ini'
        """
        search_path = os.path.join(self.data_root, filename_pattern)
        files = glob.glob(search_path)
        
        if not files:
            print(f"Warning: No files found for variable '{var_name}' with pattern '{search_path}'")
            return

        self.data_sources[var_name] = {}
        found_times = set()

        for f in files:
            t_idx = extract_time_index(os.path.basename(f))
            if t_idx != -1:
                self.data_sources[var_name][t_idx] = f
                found_times.add(t_idx)
        
        # Update available times (intersection of all variables to ensure alignment)
        if not self.available_times:
            self.available_times = found_times
        else:
            self.available_times = self.available_times.intersection(found_times)
        
        print(f"Registered '{var_name}': {len(found_times)} files found.")

    def process_sequence(self, output_dir, criteria_expression, mesh_name_prefix="watermass"):
        """
        Process the sequence using a logical expression.
        criteria_expression: string using numpy syntax, e.g. "(temp < 15) & (salt > 33)"
        """
        if not self.data_sources:
            print("No variables registered.")
            return

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        sorted_times = sorted(list(self.available_times))
        print(f"Processing {len(sorted_times)} aligned time steps...")
        print(f"Criteria: {criteria_expression}")

        trajectory = []

        for t_idx in sorted_times:
            print(f"Time Step {t_idx}...")
            
            # 1. Load all variables for this time step
            frame_vars = {}
            ref_meta = None
            
            try:
                for var_name, files_map in self.data_sources.items():
                    path = files_map[t_idx]
                    vol, meta = load_volume_from_ini(path)
                    frame_vars[var_name] = vol
                    if ref_meta is None: ref_meta = meta
                
                # 2. Evaluate Expression
                # We use python's eval inside a context where keys are variables
                # numpy logic operators: & (and), | (or), ~ (not)
                # User defined expression must use these unless we use numexpr
                
                # Create a local dictionary for eval
                context = frame_vars
                
                # Calculate Mask
                # WARNING: eval is unsafe if input is untrusted. Assuming trusted internal use.
                try:
                    mask = eval(criteria_expression, {"__builtins__": None}, context)
                except Exception as e:
                    print(f"  Error calculating logic: {e}")
                    continue
                
                if not isinstance(mask, np.ndarray) or mask.dtype != bool:
                    print("  Expression did not result in a boolean array.")
                    continue

                # 3. Extract Mesh (if mask is not empty)
                if np.any(mask):
                    # Marching Cubes requires a float volume for iso-level. 
                    # If we have a binary mask, the boundary is between 0 and 1. Level=0.5 works.
                    mask_float = mask.astype(np.float32)
                    
                    # Optimization: Create mesh only if mask is not empty
                    verts, faces, normals, values = measure.marching_cubes(mask_float, level=0.5, step_size=1)
                    
                    # Convert to Unity coords (Swap Y/Z or as needed)
                    # Current assumption: Z, Y, X -> Unity X, Y, Z
                    # We map: col 2 (X) -> x, col 1 (Y) -> y, col 0 (Z) -> z
                    verts_xyz = verts[:, [2, 1, 0]]
                    
                    # Save mesh
                    mesh_path = os.path.join(output_dir, f"{mesh_name_prefix}_t{t_idx}.obj")
                    save_obj(verts_xyz, faces, mesh_path)
                    
                    # 4. Calculate Centroid
                    # Use indices average for geometric center of the water mass
                    indices = np.argwhere(mask)
                    center_z, center_y, center_x = np.average(indices, axis=0) # Geometric center
                    centroid = (float(center_x), float(center_y), float(center_z))
                    
                    trajectory.append({
                        "time_index": t_idx,
                        "centroid": centroid,
                        "volume_voxels": int(np.sum(mask))
                    })
                    print(f"  Target found. Centroid: {centroid}. Saved mesh.")
                else:
                    print("  No region matches criteria.")
                    trajectory.append({
                        "time_index": t_idx,
                        "centroid": None,
                        "volume_voxels": 0
                    })

            except Exception as e:
                print(f"  Error processing frame {t_idx}: {e}")

        # Save Trajectory
        with open(os.path.join(output_dir, f"{mesh_name_prefix}_trajectory.json"), 'w') as f:
            json.dump(trajectory, f, indent=4)

if __name__ == "__main__":
    import sys
    
    # Default Paths - 指向 Unity 项目的 MyData 文件夹
    try:
        base_dir = os.path.dirname(__file__)
    except NameError:
        base_dir = "."
    
    # Unity MyData 文件夹路径
    WORKSPACE_DIR = os.path.abspath(os.path.join(base_dir, "../RenderingModule/Assets/MyData"))
    OUTPUT_DIR = os.path.abspath(os.path.join(base_dir, "../RenderingModule/Assets/WaterMassOutput"))

    # User Configuration
    # You can also pass these as arguments
    if len(sys.argv) > 1:
        WORKSPACE_DIR = sys.argv[1]
    
    print(f"Data Source: {WORKSPACE_DIR}")
    print(f"Output Dir:  {OUTPUT_DIR}")
    
    processor = WaterMassProcessor(WORKSPACE_DIR)
    
    # 1. 注册三个海洋变量
    processor.register_variable("chloro", "chlorophyll/*chlorophyll*.raw.ini")  # 叶绿素
    processor.register_variable("no3",    "NO3/*NO3*.raw.ini")                   # 硝酸盐
    processor.register_variable("salt",   "salt/*salt*.raw.ini")                 # 盐度
    
    # 2. 定义水团逻辑公式
    # 示例：高叶绿素(>50) + 低硝酸盐(<100) + 中等盐度(30-200) 的区域
    # 值范围是 0-255 (uint8 归一化数据)
    # 您可以根据海洋学家的建议修改这些阈值
    logic = "(chloro > 50) & (no3 < 100) & (salt > 30) & (salt < 200)"
    
    print(f"Executing Logic: {logic}")
    
    # 3. 执行处理
    processor.process_sequence(OUTPUT_DIR, logic, mesh_name_prefix="MultiVar_WaterMass")
