import os
import numpy as np

def inspect_volume_data(ini_path):
    print(f"--- 正在检查文件: {ini_path} ---")
    
    if not os.path.exists(ini_path):
        print(f"错误: 找不到文件 {ini_path}")
        return

    params = {}
    try:
        with open(ini_path, 'r') as f:
            print("\n[INI 文件内容预览]:")
            for line in f:
                line = line.strip()
                print(f"  {line}")
                # 适配冒号分隔符
                if ':' in line:
                    key, value = line.split(':', 1)
                    params[key.strip().lower()] = value.strip()
                elif '=' in line:
                    key, value = line.split('=', 1)
                    params[key.strip().lower()] = value.strip()
    except Exception as e:
        print(f"读取 INI 文件失败: {e}")
        return

    # 尝试解析尺寸
    width = int(params.get('dimx', 0))
    height = int(params.get('dimy', 0))
    depth = int(params.get('dimz', 0))
    
    # 尝试解析格式
    fmt = params.get('format', 'uint8').lower()
    
    # 尝试推断 raw 文件名 (通常同名，只是后缀不同)
    # 假设 raw 文件名是把 .raw.ini 去掉 .ini 或者直接同名 .raw
    base_name = os.path.splitext(ini_path)[0] # 去掉 .ini
    # 如果文件名本身包含 .raw (例如 data.raw.ini -> data.raw)
    raw_path_guess_1 = base_name 
    # 如果文件名不包含 .raw (例如 data.ini -> data.raw)
    raw_path_guess_2 = os.path.splitext(base_name)[0] + ".raw"
    
    raw_path = raw_path_guess_1 if os.path.exists(raw_path_guess_1) else raw_path_guess_2

    if width == 0 or height == 0 or depth == 0:
        print("\n❌ 错误: 无法解析维度信息 (dimx, dimy, dimz)")
        return

    print(f"\n[解析结果]:")
    print(f"  尺寸 (X, Y, Z): {width} x {height} x {depth}")
    print(f"  总像素点数: {width * height * depth:,}")

    # 解析数据类型
    type_map = {
        'uint8': (np.uint8, 1),
        'uchar': (np.uint8, 1),
        'uint16': (np.uint16, 2),
        'ushort': (np.uint16, 2),
        'int16': (np.int16, 2),
        'short': (np.int16, 2),
        'float': (np.float32, 4),
        'float32': (np.float32, 4),
        'double': (np.float64, 8)
    }
    
    dtype_info = type_map.get(fmt)
    if dtype_info:
        dtype, bytes_per_pixel = dtype_info
        expected_size = width * height * depth * bytes_per_pixel
        print(f"  数据类型: {fmt} ({bytes_per_pixel} bytes/pixel)")
        print(f"  预期 RAW 文件大小: {expected_size:,} bytes ({expected_size/1024/1024:.2f} MB)")
    else:
        print(f"  未知数据类型: {fmt}")
        expected_size = -1

    # 检查 RAW 文件
    if os.path.exists(raw_path):
        actual_size = os.path.getsize(raw_path)
        print(f"\n[RAW 文件检查]:")
        print(f"  文件路径: {raw_path}")
        print(f"  实际大小: {actual_size:,} bytes")
        
        if expected_size != -1:
            if actual_size == expected_size:
                print("  ✅ 校验成功: 文件大小与配置完全匹配。")
            else:
                print(f"  ❌ 校验失败: 大小不匹配! 差值: {actual_size - expected_size} bytes")
                # 检查是否是因为头部信息
                skip_bytes = int(params.get('skip', 0))
                if actual_size - skip_bytes == expected_size:
                     print(f"  ⚠️ 注意: 扣除 skip 字节 ({skip_bytes}) 后匹配成功。")
    else:
        print(f"\n❌ 错误: 找不到对应的 RAW 文件。尝试了: {raw_path}")

if __name__ == "__main__":
    target_file = "OneDayData/volume_oxygen_data_time_0_255.raw.ini"
    inspect_volume_data(target_file)