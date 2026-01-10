import numpy as np
import os

def fit_to_scene(ini_path, unity_size):
    print(f"--- 开始适配场景数据 ---")
    
    # Unity 场景尺寸
    u_x, u_y, u_z = unity_size
    print(f"目标 Unity 场景: X={u_x}, Y(高)={u_y}, Z={u_z}")
    target_ratio = u_x / u_z
    print(f"目标水平比例 (X/Z): {target_ratio:.3f}")

    # 1. 读取原始数据
    params = {}
    with open(ini_path, 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                params[key.strip().lower()] = value.strip()
    
    width = int(params['dimx'])   # Data X
    height = int(params['dimy'])  # Data Y (对应 Unity Z)
    depth = int(params['dimz'])   # Data Z (对应 Unity Y)
    fmt = params.get('format', 'uint8')
    
    print(f"原始数据尺寸: X={width}, Y={height}, Z={depth}")
    data_ratio = width / height
    print(f"原始数据比例 (X/Y): {data_ratio:.3f}")

    # 读取二进制
    type_map = {'uint8': np.uint8, 'uchar': np.uint8}
    dtype = type_map.get(fmt, np.uint8)
    raw_path = os.path.splitext(ini_path)[0]
    if not os.path.exists(raw_path) and not raw_path.endswith('.raw'): raw_path += ".raw"
    data = np.fromfile(raw_path, dtype=dtype)
    volume = data.reshape((depth, height, width)) # (Z, Y, X)

    # 2. 计算裁剪范围 (保持中心裁剪)
    # 我们需要让 New_X / New_Y = target_ratio
    
    if data_ratio > target_ratio:
        # 数据太宽，需要裁掉 X 轴两边
        new_width = int(height * target_ratio)
        new_height = height
        start_x = (width - new_width) // 2
        crop_slice = (slice(None), slice(None), slice(start_x, start_x + new_width))
        print(f"策略: 裁剪 X 轴。保留 X: [{start_x} : {start_x + new_width}]")
    else:
        # 数据太长，需要裁掉 Y 轴两边
        new_width = width
        new_height = int(width / target_ratio)
        start_y = (height - new_height) // 2
        crop_slice = (slice(None), slice(start_y, start_y + new_height), slice(None))
        print(f"策略: 裁剪 Y 轴。保留 Y: [{start_y} : {start_y + new_height}]")

    cropped_vol = volume[crop_slice]

    # 3. 降采样 (解决卡顿的关键)
    # 强制进行 2 倍降采样
    downsample_factor = 2
    final_vol = cropped_vol[::downsample_factor, ::downsample_factor, ::downsample_factor] # Z, Y, X 都降
    
    d_depth, d_height, d_width = final_vol.shape
    
    print(f"--------------------------------")
    print(f"处理后最终尺寸: {d_width} x {d_height} x {d_depth}")
    print(f"原始点数: {width*height*depth:,}")
    print(f"最终点数: {d_width*d_height*d_depth:,}")
    print(f"性能优化: 数据量减少了 {(1 - (d_width*d_height*d_depth)/(width*height*depth))*100:.1f}%")
    print(f"--------------------------------")

    # 4. 保存
    base_dir = os.path.dirname(ini_path)
    output_name = "Scene_Adapted_Data"
    out_raw = os.path.join(base_dir, f"{output_name}.raw")
    out_ini = os.path.join(base_dir, f"{output_name}.raw.ini")

    final_vol.tofile(out_raw)
    with open(out_ini, 'w') as f:
        f.write(f"dimx:{d_width}\n")
        f.write(f"dimy:{d_height}\n")
        f.write(f"dimz:{d_depth}\n")
        f.write(f"skip:0\n")
        f.write(f"format:{fmt}\n")

    print(f"✅ 文件已生成: {out_raw}")
    print(f"💡 Unity 设置提示: 请将 Volume Object 的 Scale 设置为 ({u_x}, {u_y}, {u_z})")

if __name__ == "__main__":
    INPUT_FILE = "OneDayData/volume_oxygen_data_time_0_255.raw.ini"
    
    # 您的 Unity 场景尺寸
    UNITY_SCENE_SIZE = (200, 100, 300) # X, Y(高), Z
    
    fit_to_scene(INPUT_FILE, UNITY_SCENE_SIZE)