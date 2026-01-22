import os
import glob
import re
import numpy as np
import json
from skimage import measure
try:
    from .volume_loader import load_volume_from_ini
except ImportError:
    from volume_loader import load_volume_from_ini

def save_obj(vertices, faces, output_path):
    """
    Save mesh to OBJ file.
    """
    with open(output_path, 'w') as f:
        f.write("# Water Mass Mesh\n")
        for v in vertices:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        
        # OBJ faces are 1-indexed
        for face in faces:
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def process_directory(input_dir, output_dir, threshold=50, variable_name="chlorophyll"):
    """
    Process all .raw.ini files in the directory, extract isosurfaces, and save them.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Find all .ini files
    pattern = os.path.join(input_dir, f"*{variable_name}*.raw.ini")
    files = glob.glob(pattern)
    files.sort(key=natural_sort_key)

    if not files:
        print(f"No files found matching pattern: {pattern}")
        return

    print(f"Found {len(files)} files.")
    
    for i, ini_path in enumerate(files):
        print(f"Processing frame {i}: {os.path.basename(ini_path)}")
        
        try:
            # 1. Load Data
            volume, meta = load_volume_from_ini(ini_path)
            
            # 2. Threshold / Filter
            # For this demo, we assume a simple threshold. 
            # In future, this could be a complex boolean mask passed in.
            # volume is shape (Z, Y, X).
            # Marching cubes expects (M, N, P).
            
            # Check range
            min_val, max_val = volume.min(), volume.max()
            # print(f"  Range: [{min_val}, {max_val}]")
            
            if max_val < threshold:
                print(f"  Skipping: Max value {max_val} provided is below threshold {threshold}")
                continue

            # 3. Marching Cubes
            # level is the Isovalue
            # step_size can be increased to reduce mesh complexity (LOD)
            verts, faces, normals, values = measure.marching_cubes(volume, level=threshold, step_size=2)
            
            # Transform vertices?
            # Vertices come out as (row, col, slice) -> (Z, Y, X) order in numpy?
            # skimage documentation: returns (row, col, slice).
            # Our volume is (Z, Y, X). So verts are (z, y, x).
            # Unity is (x, y, z). We might need to swap columns.
            # Let's simple swap columns 0 and 2 to match (x, y, z).
            # Z is 0, Y is 1, X is 2 -> X=2, Y=1, Z=0.
            verts_xyz = verts[:, [2, 1, 0]]
            
            # 4. Save
            out_name = os.path.basename(ini_path).replace('.raw.ini', '.obj')
            out_name = out_name.replace('.ini', '.obj') # Safety
            save_path = os.path.join(output_dir, out_name)
            
            save_obj(verts_xyz, faces, save_path)
            print(f"  Saved mesh to {save_path} (Verts: {len(verts_xyz)})")

        except Exception as e:
            print(f"  Error processing {ini_path}: {e}")

if __name__ == "__main__":
    # Example Usage
    # You can change these paths
    INPUT_DIR = "/Users/yiquan/Downloads/OneDrive_21_2026-1-21" 
    OUTPUT_DIR = "ExtractedMeshes"
    THRESHOLD = 10 # Example threshold for Chlorophyll (assuming 0-255 range, modify as needed)
    
    process_directory(INPUT_DIR, OUTPUT_DIR, threshold=THRESHOLD, variable_name="chlorophyll")
