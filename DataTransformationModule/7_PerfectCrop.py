import numpy as np
import os

def perfect_crop_to_scene(ini_path, unity_size):
    print(f"--- 开始完美比例裁剪 ---")
    
    # Unity 场景尺寸 (X, Y=高, Z=长)
    u_x, u_y, u_z = unity_size
    print(f"Unity 场景目标: 宽(X)={u_x}, 深(Z)={u_z}, 高(Y)={u_y}")
    
    # 计算目标比例 (以高度 Y 为基准 1)
    # 比例格式: X : Z : Y
    ratio_x = u_x / u_y
    ratio_z = u_z / u_y
    print(f"目标几何比例 (X : Z : Y) = {ratio_x:.2f} : {ratio_z:.2f} : 1.00")

    # 1. 读取原始数据
    params = {}
    with open(ini_path, 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                params[key.strip().lower()] = value.strip()
    
    raw_w = int(params['dimx'])   # Data X
    raw_h = int(params['dimy'])   # Data Y (对应 Unity Z)
    raw_d = int(params['dimz'])   # Data Z (对应 Unity Y)
    fmt = params.get('format', 'uint8')
    
    print(f"原始数据尺寸: X={raw_w}, Y={raw_h}, Z={raw_d}")

    # 2. 计算最大裁剪尺寸
    # 我们尝试以 Z 轴 (深度) 为基准，因为它通常最小
    # Data Z 对应 Unity Y
    
    # 方案 A: 以 Data Z (92) 为基准
    base_size = raw_d
    target_x = int(base_size * ratio_x)
    target_y = int(base_size * ratio_z) # Data Y 对应 Unity Z
    target_z = base_size

    # 检查是否越界
    if target_x > raw_w or target_y > raw_h:
        print("警告: 以深度为基准裁剪会超出原始范围，尝试缩小基准...")
        # 这里可以添加更复杂的逻辑来适配，但通常海洋数据 Z 轴都是最小的，所以方案 A 通常有效
        # 如果越界，取能满足的最大比例
        scale = min(raw_w / ratio_x, raw_h / ratio_z, raw_d / 1.0)
        target_x = int(scale * ratio_x)
        target_y = int(scale * ratio_z)
        target_z = int(scale)

    print(f"--------------------------------")
    print(f"计算出的裁剪尺寸: {target_x} (X) x {target_y} (Y) x {target_z} (Z)")
    print(f"对应 Unity 比例: {target_x} : {target_y} : {target_z} ≈ {u_x} : {u_z} : {u_y}")
    print(f"--------------------------------")

    # 3. 读取并裁剪
    type_map = {'uint8': np.uint8, 'uchar': np.uint8}
    dtype = type_map.get(fmt, np.uint8)
    raw_path = os.path.splitext(ini_path)[0]
    if not os.path.exists(raw_path) and not raw_path.endswith('.raw'): raw_path += ".raw"
    
    data = np.fromfile(raw_path, dtype=dtype)
    volume = data.reshape((raw_d, raw_h, raw_w)) # (Z, Y, X)

    # 中心裁剪
    start_z = (raw_d - target_z) // 2
    start_y = (raw_h - target_y) // 2
    start_x = (raw_w - target_x) // 2

    print(f"裁剪区域 -> X:[{start_x}:{start_x+target_x}], Y:[{start_y}:{start_y+target_y}], Z:[{start_z}:{start_z+target_z}]")

    cropped_vol = volume[
        start_z : start_z + target_z,
        start_y : start_y + target_y,
        start_x : start_x + target_x
    ]

    # 4. 降采样 (可选，为了性能建议保留)
    # 如果您想要最高精度，可以把 factor 改为 1
    downsample_factor = 1 
    if downsample_factor > 1:
        print(f"正在进行 {downsample_factor} 倍降采样以优化性能...")
        cropped_vol = cropped_vol[::downsample_factor, ::downsample_factor, ::downsample_factor]

    final_d, final_h, final_w = cropped_vol.shape

    # 5. 保存
    base_dir = os.path.dirname(ini_path)
    output_name = "Scene_Perfect_Crop"
    out_raw = os.path.join(base_dir, f"{output_name}.raw")
    out_ini = os.path.join(base_dir, f"{output_name}.raw.ini")

    cropped_vol.tofile(out_raw)
    with open(out_ini, 'w') as f:
        f.write(f"dimx:{final_w}\n")
        f.write(f"dimy:{final_h}\n")
        f.write(f"dimz:{final_d}\n")
        f.write(f"skip:0\n")
        f.write(f"format:{fmt}\n")

    print(f"✅ 文件已生成: {out_raw}")
    print(f"💡 Unity 设置: Scale 设为 ({u_x}, {u_y}, {u_z}) 时，数据将完美无变形。")

if __name__ == "__main__":
    INPUT_FILE = "OneDayData/volume_oxygen_data_time_0_255.raw.ini"
    
    # 您的 Unity 场景尺寸 (X, Y=高, Z=长)
    # 请确保这里填写的和您 Unity 里的一模一样
    UNITY_SCENE_SIZE = (200, 100, 300) 
    
    perfect_crop_to_scene(INPUT_FILE, UNITY_SCENE_SIZE)