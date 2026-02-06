#!/usr/bin/env python3
"""检查数据对比"""
import numpy as np

# 对比原始数据和我们生成的数据
orig_path = '/Users/yiquan/Desktop/VolumeSTCube/RenderingModule/Assets/MyData/chlorophyll/volume_chlorophyll_data_time_0_255.raw'
new_path = '/Users/yiquan/Desktop/VolumeSTCube/RenderingModule/Assets/WaterMassHighlighted/water_mass_highlighted_t0.raw'

orig = np.fromfile(orig_path, dtype=np.uint8).reshape((92, 441, 400))
new = np.fromfile(new_path, dtype=np.uint8).reshape((92, 441, 400))

print('=== 原始叶绿素数据 ===')
print(f'零值: {np.sum(orig == 0):,} ({100*np.sum(orig==0)/orig.size:.1f}%)')
print(f'非零: {np.sum(orig > 0):,}')
print(f'Range: [{orig.min()}, {orig.max()}]')

print('\n=== 我们生成的数据 ===')
print(f'零值: {np.sum(new == 0):,} ({100*np.sum(new==0)/new.size:.1f}%)')
print(f'非零: {np.sum(new > 0):,}')
print(f'Range: [{new.min()}, {new.max()}]')

# 水团区域 (200-255)
water_mass = np.sum((new >= 200) & (new <= 255))
print(f'水团区域 (200-255): {water_mass:,}')

# 检查零值位置是否一致
orig_zero_mask = (orig == 0)
new_zero_mask = (new == 0)
match = np.sum(orig_zero_mask == new_zero_mask)
print(f'\n零值位置匹配: {match:,} / {orig.size:,} ({100*match/orig.size:.1f}%)')

# 非水团区域是否保持原值
non_water = (new < 200) & (new > 0)
orig_non_water = orig[non_water]
new_non_water = new[non_water]
if len(orig_non_water) > 0:
    same = np.sum(orig_non_water == new_non_water)
    print(f'非水团区域值匹配: {same:,} / {len(orig_non_water):,} ({100*same/len(orig_non_water):.1f}%)')
