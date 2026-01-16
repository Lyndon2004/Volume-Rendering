# -*- coding: utf-8 -*-
"""
直接处理已有 RAW 文件的边界改进脚本
用于优化 volume_oxygen_data_time_0_255.raw 的边界

无需依赖 InterpolateResult 的 JSON 文件
"""

import numpy as np
import os
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(__file__)


def neumann_boundary(data_3d, boundary_width=2):
    """
    Neumann 边界条件：用相邻内部值替代边界值
    避免边界的人工低值
    """
    data = data_3d.copy()
    z, x, y = data.shape
    
    print(f"  应用 Neumann 边界条件 (宽度={boundary_width})...")
    
    # 处理 Z 轴（深度）
    for i in range(boundary_width):
        if i < z:
            data[i, :, :] = data[boundary_width, :, :]
            data[-(i+1), :, :] = data[-(boundary_width+1), :, :]
    
    # 处理 X 轴（宽度）
    for i in range(boundary_width):
        if i < x:
            data[:, i, :] = data[:, boundary_width, :]
            data[:, -(i+1), :] = data[:, -(boundary_width+1), :]
    
    # 处理 Y 轴（高度）
    for i in range(boundary_width):
        if i < y:
            data[:, :, i] = data[:, :, boundary_width]
            data[:, :, -(i+1)] = data[:, :, -(boundary_width+1)]
    
    return data


def gaussian_smooth_boundary(data_3d, sigma=1.5, boundary_fade_width=5):
    """
    高斯模糊平滑边界，创建自然的过渡
    """
    print(f"  应用高斯平滑 (sigma={sigma}, 淡出宽度={boundary_fade_width})...")
    
    blurred = gaussian_filter(data_3d.astype(float), sigma=sigma)
    
    z, x, y = data_3d.shape
    mask = np.ones_like(data_3d, dtype=float)
    
    # 创建边界淡出掩膜
    for i in range(boundary_fade_width):
        fade = (boundary_fade_width - i) / boundary_fade_width
        mask[i, :, :] *= fade
        mask[-(i+1), :, :] *= fade
        mask[:, i, :] *= fade
        mask[:, -(i+1), :] *= fade
        mask[:, :, i] *= fade
        mask[:, :, -(i+1)] *= fade
    
    result = data_3d * mask + blurred * (1 - mask)
    return result.astype(np.uint8)


def process_raw_file(input_path, output_path, dims, boundary_method='neumann'):
    """
    处理 RAW 文件，应用边界改进
    
    Args:
        input_path: 输入 .raw 文件路径
        output_path: 输出 .raw 文件路径
        dims: (x, y, z) 维度元组
        boundary_method: 'neumann' 或 'gaussian'
    """
    print(f"\n开始处理: {os.path.basename(input_path)}")
    print(f"  尺寸: {dims[0]} × {dims[1]} × {dims[2]}")
    
    # 1. 读取数据
    print("  读取数据...")
    data = np.fromfile(input_path, dtype=np.uint8)
    data_3d = data.reshape((dims[0], dims[1], dims[2]))  # (x, y, z)
    
    # 打印数据统计
    print(f"  数据范围: {data_3d.min()} ~ {data_3d.max()}")
    print(f"  数据平均值: {data_3d.mean():.1f}")
    print(f"  数据中位数: {np.median(data_3d):.1f}")
    
    # 2. 应用边界处理
    if boundary_method == 'neumann':
        data_3d = neumann_boundary(data_3d, boundary_width=3)
    elif boundary_method == 'gaussian':
        data_3d = gaussian_smooth_boundary(data_3d, sigma=1.5, boundary_fade_width=5)
    else:
        print(f"  警告: 未知的边界方法 {boundary_method}，跳过处理")
    
    # 3. 保存数据
    print("  保存数据...")
    data_3d.astype(np.uint8).tofile(output_path)
    
    print(f"✓ 完成: {os.path.basename(output_path)}")
    return output_path


def main():
    """
    主流程：处理所有需要的数据文件
    """
    
    print("="*60)
    print("海洋含氧量数据 - 边界改进处理")
    print("="*60)
    
    # 原始数据文件信息
    raw_file_path = os.path.join(HERE, 'OneDayData', 'volume_oxygen_data_time_0_255.raw')
    raw_ini_path = os.path.join(HERE, 'OneDayData', 'volume_oxygen_data_time_0_255.raw.ini')
    
    # 检查文件是否存在
    if not os.path.exists(raw_file_path):
        print(f"✗ 错误: 找不到文件 {raw_file_path}")
        return
    
    if not os.path.exists(raw_ini_path):
        print(f"✗ 错误: 找不到文件 {raw_ini_path}")
        return
    
    # 读取 INI 文件获取维度
    dims = {}
    with open(raw_ini_path, 'r') as f:
        for line in f:
            if ':' in line:
                key, value = line.split(':')
                key = key.strip().lower()
                value = value.strip()
                if key == 'dimx':
                    dims['x'] = int(value)
                elif key == 'dimy':
                    dims['y'] = int(value)
                elif key == 'dimz':
                    dims['z'] = int(value)
    
    if len(dims) != 3:
        print(f"✗ 错误: 无法从 INI 文件读取完整的维度信息")
        return
    
    print(f"\n[输入数据信息]")
    print(f"  文件: {os.path.basename(raw_file_path)}")
    print(f"  维度: X={dims['x']}, Y={dims['y']}, Z={dims['z']}")
    
    # 创建输出目录
    output_dir = os.path.join(HERE, 'MyData')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"\n  创建输出目录: {output_dir}")
    
    # ====================================================================
    # 方案 A：Neumann 边界（推荐）
    # ====================================================================
    print("\n[方案 A] Neumann 边界处理")
    output_path_neumann = os.path.join(output_dir, 'volume_oxygen_neumann_boundary.raw')
    process_raw_file(
        raw_file_path,
        output_path_neumann,
        (dims['x'], dims['y'], dims['z']),
        boundary_method='neumann'
    )
    
    # 生成 INI 文件
    ini_content = f"dimx:{dims['x']} \ndimy:{dims['y']} \ndimz:{dims['z']} \nskip:0 \nformat:uint8"
    with open(output_path_neumann + '.ini', 'w') as f:
        f.write(ini_content)
    print(f"  配置文件: {os.path.basename(output_path_neumann)}.ini")
    
    # ====================================================================
    # 方案 B：高斯平滑边界
    # ====================================================================
    print("\n[方案 B] 高斯平滑边界处理")
    output_path_gaussian = os.path.join(output_dir, 'volume_oxygen_gaussian_boundary.raw')
    process_raw_file(
        raw_file_path,
        output_path_gaussian,
        (dims['x'], dims['y'], dims['z']),
        boundary_method='gaussian'
    )
    
    # 生成 INI 文件
    with open(output_path_gaussian + '.ini', 'w') as f:
        f.write(ini_content)
    print(f"  配置文件: {os.path.basename(output_path_gaussian)}.ini")
    
    # ====================================================================
    # 对比分析
    # ====================================================================
    print("\n[对比分析]")
    print(f"  原始文件: {output_dir}/volume_oxygen_data_time_0_255.raw")
    print(f"  Neumann处理: {output_dir}/volume_oxygen_neumann_boundary.raw")
    print(f"  高斯处理: {output_dir}/volume_oxygen_gaussian_boundary.raw")
    print("\n建议:")
    print("  1. 在 Unity 中加载这三个文件进行对比")
    print("  2. 用 T 键切换 Transfer Function，观察边界变化")
    print("  3. 选择视觉效果最好的版本")
    print("  4. 如满意，可将其作为最终数据")
    
    print("\n" + "="*60)
    print("✓ 处理完成！")
    print("="*60)


if __name__ == '__main__':
    main()
