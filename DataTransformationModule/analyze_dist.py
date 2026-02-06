#!/usr/bin/env python3
import numpy as np

path = '/Users/yiquan/Desktop/VolumeSTCube/RenderingModule/Assets/WaterMassHighlighted/water_mass_highlighted_t0.raw'
data = np.fromfile(path, dtype=np.uint8)

print('=== 值分布分析 ===')
print(f'Total voxels: {len(data):,}')

print(f'值=0 (透明): {np.sum(data == 0):,} ({100*np.sum(data==0)/len(data):.1f}%)')
print(f'值=1-50: {np.sum((data >= 1) & (data <= 50)):,}')
print(f'值=51-100: {np.sum((data >= 51) & (data <= 100)):,}')
print(f'值=101-150: {np.sum((data >= 101) & (data <= 150)):,}')
print(f'值=151-199: {np.sum((data >= 151) & (data <= 199)):,}')
print(f'值=200-255 (水团): {np.sum(data >= 200):,}')

background = data[(data > 0) & (data < 200)]
print(f'\n背景 (1-199): min={background.min()}, max={background.max()}, mean={background.mean():.1f}')

watermass = data[data >= 200]
print(f'水团 (200-255): min={watermass.min()}, max={watermass.max()}, mean={watermass.mean():.1f}')
