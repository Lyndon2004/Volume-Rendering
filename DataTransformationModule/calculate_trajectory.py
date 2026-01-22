import os
import glob
import re
import json
import numpy as np
try:
    from .volume_loader import load_volume_from_ini
except ImportError:
    from volume_loader import load_volume_from_ini

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def calculate_centroid(volume, threshold=0):
    """
    Calculate the center of mass of the volume where value > threshold.
    """
    # Create mask
    mask = volume > threshold
    if not np.any(mask):
        return None

    # Get indices (z, y, x)
    # We want (x, y, z) for Unity usually.
    # np.argwhere returns (N, 3) array of [z, y, x] coords
    indices = np.argwhere(mask)
    
    # Get values for weighting
    values = volume[mask]
    
    # Calculate weighted average
    # axis=0 means average across the list of points
    center_z, center_y, center_x = np.average(indices, axis=0, weights=values)
    
    # Return in (x, y, z) order match Unity
    return (float(center_x), float(center_y), float(center_z))

def extract_time_index(filename):
    # Match time_X_ or time_X.
    match = re.search(r'time_(\d+)', filename)
    if match:
        return int(match.group(1))
    return -1

def process_trajectory(input_dir, output_file, threshold=50, variable_name="chlorophyll"):
    pattern = os.path.join(input_dir, f"*{variable_name}*.raw.ini")
    files = glob.glob(pattern)
    files.sort(key=natural_sort_key)

    if not files:
        print(f"No files found for trajectory calculation in {input_dir}")
        return

    trajectory_data = []

    print(f"Calculating trajectory for {len(files)} frames...")

    for ini_path in files:
        filename = os.path.basename(ini_path)
        time_idx = extract_time_index(filename)
        
        try:
            volume, meta = load_volume_from_ini(ini_path)
            
            centroid = calculate_centroid(volume, threshold)
            
            frame_data = {
                "filename": filename,
                "time_index": time_idx,
                "centroid": centroid, # [x, y, z] or null
                "has_data": centroid is not None
            }
            
            # Additional metrics
            if centroid:
                mask = volume > threshold
                frame_data["volume_voxels"] = int(np.sum(mask))
                frame_data["max_value"] = int(np.max(volume))
            
            trajectory_data.append(frame_data)
            print(f"  Frame {time_idx}: {centroid}")

        except Exception as e:
            print(f"  Error processing {filename}: {e}")

    # Save JSON
    with open(output_file, 'w') as f:
        json.dump(trajectory_data, f, indent=4)
    print(f"Trajectory saved to {output_file}")

if __name__ == "__main__":
    INPUT_DIR = "/Users/yiquan/Downloads/OneDrive_21_2026-1-21"
    OUTPUT_FILE = "trajectory.json"
    THRESHOLD = 10
    
    process_trajectory(INPUT_DIR, OUTPUT_FILE, threshold=THRESHOLD, variable_name="chlorophyll")
