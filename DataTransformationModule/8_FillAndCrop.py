import numpy as np
import os
import sys

def fill_and_crop(ini_path, unity_size):
    # 检查 scipy
    try:
        from scipy import ndimage
    except ImportError:
        print("❌ 错误: 缺少 scipy 库。请运行: pip install scipy")
        return

    print(f"--- 开始处理: 完美裁剪 + 智能补全 ---")
    
    # Unity 场景尺寸
    u_x, u_y, u_z = unity_size
    # 比例: X : Z : Y (以 Y 高度为基准)
    ratio_x = u_x / u_y
    ratio_z = u_z / u_y
    print(f"目标比例 (X:Z:Y) = {ratio_x:.2f} : {ratio_z:.2f} : 1.0")

    # 1. 读取数据
    params = {}
    with open(ini_path, 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                params[key.strip().lower()] = value.strip()
    
    raw_w = int(params['dimx'])
    raw_h = int(params['dimy'])
    raw_d = int(params['dimz'])
    fmt = params.get('format', 'uint8')
    
    type_map = {'uint8': np.uint8, 'uchar': np.uint8}
    dtype = type_map.get(fmt, np.uint8)
    raw_path = os.path.splitext(ini_path)[0]
    if not os.path.exists(raw_path) and not raw_path.endswith('.raw'): raw_path += ".raw"
    
    data = np.fromfile(raw_path, dtype=dtype)
    volume = data.reshape((raw_d, raw_h, raw_w)) # Z, Y, X

    # 2. 计算裁剪尺寸 (保持 7_PerfectCrop 的逻辑)
    base_size = raw_d
    target_x = int(base_size * ratio_x)
    target_y = int(base_size * ratio_z)
    target_z = base_size

    # 防止越界
    if target_x > raw_w or target_y > raw_h:
        scale = min(raw_w / ratio_x, raw_h / ratio_z, raw_d / 1.0)
        target_x = int(scale * ratio_x)
        target_y = int(scale * ratio_z)
        target_z = int(scale)

    # 中心裁剪
    start_z = (raw_d - target_z) // 2
    start_y = (raw_h - target_y) // 2
    start_x = (raw_w - target_x) // 2
    
    cropped_vol = volume[
        start_z : start_z + target_z,
        start_y : start_y + target_y,
        start_x : start_x + target_x
    ]
    
    print(f"裁剪完成，尺寸: {target_x} x {target_y} x {target_z}")

    # 3. 执行智能补全 (Inpainting)
    print("⏳ 正在执行智能补全 (填补空缺)... 这可能需要几秒钟...")
    
    # 假设 0 是空值
    # 计算每个 0 点到最近非 0 点的索引
    # indices[0] 是 Z 轴索引, indices[1] 是 Y 轴, indices[2] 是 X 轴
    indices = ndimage.distance_transform_edt(cropped_vol == 0, return_distances=False, return_indices=True)
    
    # 使用索引映射，把最近的有效值填入空位
    filled_vol = cropped_vol[tuple(indices)]
    
    # 4. 保存
    base_dir = os.path.dirname(ini_path)
    output_name = "Scene_Full_Filled"
    out_raw = os.path.join(base_dir, f"{output_name}.raw")
    out_ini = os.path.join(base_dir, f"{output_name}.raw.ini")

    filled_vol.tofile(out_raw)
    with open(out_ini, 'w') as f:
        f.write(f"dimx:{target_x}\n")
        f.write(f"dimy:{target_y}\n")
        f.write(f"dimz:{target_z}\n")
        f.write(f"skip:0\n")
        f.write(f"format:{fmt}\n")

    print(f"✅ 处理完成！")
    print(f"文件已生成: {out_raw}")
    print(f"现在这是一个实心的长方体数据了，导入 Unity 后不会有缺角。")

if __name__ == "__main__":
    INPUT_FILE = "OneDayData/volume_oxygen_data_time_0_255.raw.ini"
    UNITY_SCENE_SIZE = (200, 100, 300) # X, Y, Z
    
    fill_and_crop(INPUT_FILE, UNITY_SCENE_SIZE)