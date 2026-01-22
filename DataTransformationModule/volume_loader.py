import os
import numpy as np

def load_volume_from_ini(ini_path):
    """
    Load a raw volume based on its .ini description file.
    Returns: (volume_data, metadata_dict)
    """
    if not os.path.exists(ini_path):
        raise FileNotFoundError(f"INI file not found: {ini_path}")

    params = {}
    with open(ini_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            if ':' in line:
                key, value = line.split(':', 1)
                params[key.strip().lower()] = value.strip()
            elif '=' in line:
                key, value = line.split('=', 1)
                params[key.strip().lower()] = value.strip()

    dimx = int(params.get('dimx', 0))
    dimy = int(params.get('dimy', 0))
    dimz = int(params.get('dimz', 0))
    dtype_str = params.get('format', 'uint8').lower()
    
    # Map format string to numpy dtype
    if 'uint8' in dtype_str:
        dtype = np.uint8
    elif 'float32' in dtype_str:
        dtype = np.float32
    elif 'float' in dtype_str: # generic float usually means 32
        dtype = np.float32 
    elif 'uint16' in dtype_str:
        dtype = np.uint16
    else:
        print(f"Warning: Unknown format {dtype_str}, defaulting to uint8")
        dtype = np.uint8

    # Find raw file
    base_path = os.path.splitext(ini_path)[0] # remove .ini
    # Check for .raw suffix variation
    # 1. file.raw (if ini was file.raw.ini)
    raw_path_1 = base_path 
    # 2. file.raw (if ini was file.ini)
    raw_path_2 = base_path + ".raw"
    
    if os.path.exists(raw_path_1) and os.path.isfile(raw_path_1):
        raw_path = raw_path_1
    elif os.path.exists(raw_path_2):
        raw_path = raw_path_2
    else:
        # Fallback: maybe the ini file is named identically to the raw file but just appending .ini?
        # e.g. "data.raw" and "data.raw.ini"
        if os.path.exists(base_path):
             raw_path = base_path
        else:
            raise FileNotFoundError(f"Could not find corresponding RAW file for {ini_path}")

    # Load data
    try:
        data = np.fromfile(raw_path, dtype=dtype)
    except Exception as e:
        raise IOError(f"Failed to read raw file {raw_path}: {e}")

    expected_size = dimx * dimy * dimz
    if data.size != expected_size:
        print(f"Warning: File size {data.size} does not match dimensions {dimx}x{dimy}x{dimz}={expected_size}")
        # Try to slice or pad? For now, just raise error or reshape what we can
        # Raising error is safer
        raise ValueError("Data size mismatch")

    # Reshape
    # Unity/Texture3D usually expects [Time/Z, Height/Y, Width/X] or similar.
    # Assuming standard C order: Z, Y, X (where X is contiguous in memory)
    # Dimensions in INI: dimx, dimy, dimz
    volume = data.reshape((dimz, dimy, dimx))
    
    metadata = {
        'dimx': dimx,
        'dimy': dimy,
        'dimz': dimz,
        'dtype': dtype_str,
        'raw_path': raw_path
    }
    
    return volume, metadata
