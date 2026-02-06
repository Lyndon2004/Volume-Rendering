#!/usr/bin/env python3
"""深度对比原始数据和生成数据"""
import numpy as np

# 原始数据
orig_path = '/Users/yiquan/Desktop/VolumeSTCube/RenderingModule/Assets/MyData/chlorophyll/volume_chlorophyll_data_time_0_255.raw'
new_path = '/Users/yiquan/Desktop/VolumeSTCube/RenderingModule/Assets/WaterMassHighlighted/water_mass_highlighted_t0.raw'

# 读取原始字节（不reshape）
orig_bytes = np.fromfile(orig_path, dtype=np.uint8)
new_bytes = np.fromfile(new_path, dtype=np.uint8)

print("=== 原始数据 ===")
print(f"Size: {len(orig_bytes)}")
print(f"First 20 bytes: {orig_bytes[:20]}")

print("\n=== 我们生成的数据 ===")
print(f"Size: {len(new_bytes)}")
print(f"First 20 bytes: {new_bytes[:20]}")

# 检查是否字节完全一样（除了水团区域）
diff_count = np.sum(orig_bytes != new_bytes)
print(f"\n不同的字节数: {diff_count}")

# 找出前几个不同的位置
diff_indices = np.where(orig_bytes != new_bytes)[0][:10]
print(f"前10个不同位置: {diff_indices}")
for idx in diff_indices[:5]:
    print(f"  位置 {idx}: 原始={orig_bytes[idx]}, 新={new_bytes[idx]}")
