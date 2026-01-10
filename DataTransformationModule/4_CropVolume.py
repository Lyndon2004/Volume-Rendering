import numpy as np
import os

def crop_volume(ini_path, crop_config, output_name):
    print(f"--- 开始裁剪体积: {ini_path} ---")
    
    # 1. 解析 INI
    params = {}
    with open(ini_path, 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                params[key.strip().lower()] = value.strip()
    
    try:
        width = int(params['dimx'])
        height = int(params['dimy'])
        depth = int(params['dimz'])
        fmt = params.get('format', 'uint8')
    except KeyError:
        print("错误: INI 文件格式不正确")
        return

    print(f"原始尺寸: {width} (X) x {height} (Y) x {depth} (Z/深度)")

    # 2. 读取数据
    type_map = {'uint8': np.uint8, 'uchar': np.uint8}
    dtype = type_map.get(fmt, np.uint8)
    
    raw_path = os.path.splitext(ini_path)[0]
    if not os.path.exists(raw_path) and not raw_path.endswith('.raw'):
        raw_path += ".raw"
        
    data = np.fromfile(raw_path, dtype=dtype)
    volume = data.reshape((depth, height, width)) # 注意 numpy 顺序是 (Z, Y, X)

    # 3. 应用裁剪配置
    # config 格式: (start, end) - 如果 end 是 None，表示取到最后
    z_s, z_e = crop_config['z']
    y_s, y_e = crop_config['y']
    x_s, x_e = crop_config['x']

    # 处理默认值
    z_e = depth if z_e is None else z_e
    y_e = height if y_e is None else y_e
    x_e = width if x_e is None else x_e

    print(f"裁剪范围 -> X:[{x_s}:{x_e}], Y:[{y_s}:{y_e}], Z:[{z_s}:{z_e}]")

    # 执行切片
    cropped_volume = volume[z_s:z_e, y_s:y_e, x_s:x_e]
    
    new_depth, new_height, new_width = cropped_volume.shape
    print(f"新尺寸: {new_width} x {new_height} x {new_depth}")

    if new_width == 0 or new_height == 0 or new_depth == 0:
        print("错误: 裁剪后尺寸为 0，请检查裁剪范围。")
        return

    # 4. 保存结果
    base_dir = os.path.dirname(ini_path)
    out_raw_path = os.path.join(base_dir, f"{output_name}.raw")
    out_ini_path = os.path.join(base_dir, f"{output_name}.raw.ini")

    cropped_volume.tofile(out_raw_path)
    
    with open(out_ini_path, 'w') as f:
        f.write(f"dimx:{new_width}\n")
        f.write(f"dimy:{new_height}\n")
        f.write(f"dimz:{new_depth}\n")
        f.write(f"skip:0\n")
        f.write(f"format:{fmt}\n")
        
    print(f"✅ 裁剪完成！")
    print(f"数据: {out_raw_path}")
    print(f"配置: {out_ini_path}")

if __name__ == "__main__":
    # --- 用户配置区域 ---
    INPUT_FILE = "OneDayData/volume_oxygen_data_time_0_255.raw.ini"
    
    # 在这里定义您想要保留的范围 (Start, End)
    # 设为 None 表示"直到最后"
    # 例如：如果您只想保留表层 20 层数据，Z 设为 (0, 20)
    CROP_CONFIG = {
        'x': (0, None),   # 保留所有 X (宽度)
        'y': (0, None),   # 保留所有 Y (高度/长度)
        'z': (0, 50)      # 只保留前 50 层深度 (假设 0 是海面)
    }
    
    OUTPUT_NAME = "Oxygen_Cropped"
    # ------------------
    
    crop_volume(INPUT_FILE, CROP_CONFIG, OUTPUT_NAME)