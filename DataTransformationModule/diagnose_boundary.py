# -*- coding: utf-8 -*-
"""
诊断脚本：分析边界处理效果
"""

import numpy as np
import os

HERE = os.path.dirname(__file__)

def analyze_boundary(raw_path, dims, boundary_layers=10):
    """分析边界和内部的数据分布"""
    
    print(f"\n{'='*60}")
    print(f"边界数据诊断分析")
    print(f"{'='*60}")
    
    data = np.fromfile(raw_path, dtype=np.uint8)
    data_3d = data.reshape(dims)  # (x, y, z)
    
    x, y, z = dims
    
    print(f"\n[全局统计]")
    print(f"  总数据点: {x * y * z:,}")
    print(f"  范围: {data_3d.min()} ~ {data_3d.max()}")
    print(f"  平均值: {data_3d.mean():.2f}")
    print(f"  中位数: {np.median(data_3d):.2f}")
    print(f"  零值个数: {(data_3d == 0).sum():,} ({(data_3d == 0).sum()/len(data)*100:.1f}%)")
    
    print(f"\n[边界分析（靠近表面的层）]")
    
    # 分析各个边界
    edges = {
        "前面 (x=0~{})".format(boundary_layers): data_3d[0:boundary_layers, :, :],
        "后面 (x=-{}~)".format(boundary_layers): data_3d[-boundary_layers:, :, :],
        "左面 (y=0~{})".format(boundary_layers): data_3d[:, 0:boundary_layers, :],
        "右面 (y=-{}~)".format(boundary_layers): data_3d[:, -boundary_layers:, :],
        "上面 (z=0~{})".format(boundary_layers): data_3d[:, :, 0:boundary_layers],
        "下面 (z=-{}~)".format(boundary_layers): data_3d[:, :, -boundary_layers:],
    }
    
    for edge_name, edge_data in edges.items():
        zero_pct = (edge_data == 0).sum() / edge_data.size * 100
        print(f"  {edge_name}:")
        print(f"    范围: {edge_data.min()} ~ {edge_data.max()}")
        print(f"    平均: {edge_data.mean():.1f}  中位数: {np.median(edge_data):.1f}")
        print(f"    零值: {(edge_data == 0).sum():,} ({zero_pct:.1f}%)")
    
    print(f"\n[内部分析（中心区域）]")
    inner_margin = max(10, boundary_layers * 2)
    inner_data = data_3d[inner_margin:-inner_margin, 
                         inner_margin:-inner_margin, 
                         inner_margin:-inner_margin]
    zero_pct = (inner_data == 0).sum() / inner_data.size * 100
    print(f"  范围: {inner_data.min()} ~ {inner_data.max()}")
    print(f"  平均: {inner_data.mean():.1f}  中位数: {np.median(inner_data):.1f}")
    print(f"  零值: {(inner_data == 0).sum():,} ({zero_pct:.1f}%)")
    
    print(f"\n[诊断建议]")
    if (data_3d[0:5, :, :].mean() < 10) or ((data_3d[0:5, :, :] == 0).sum() > 0.3 * data_3d[0:5, :, :].size):
        print("  ⚠️ 边界确实存在大量低值/零值")
        print("  原因: 陆地被裁切为 0，边界附近也是陆地")
        print("  建议:")
        print("    1. 用更宽的 Neumann 处理（boundary_width=10+）")
        print("    2. 直接裁切掉边界（crop 3-5 像素）")
        print("    3. 在 Unity 中用 Min val = 0.05 忽略极低值")
    else:
        print("  ✓ 边界值合理，Neumann 处理应该有效")
        print("  可能的原因: Transfer Function 仍把低值映射到红色")
        print("  建议: 调整 Transfer Function 的低值 Alpha")


# 分析原始数据
raw_file = os.path.join(HERE, 'OneDayData', 'volume_oxygen_data_time_0_255.raw')
analyze_boundary(raw_file, (400, 441, 92), boundary_layers=10)

# 分析 Neumann 处理后的数据
neumann_file = os.path.join(HERE, 'MyData', 'volume_oxygen_neumann_boundary.raw')
if os.path.exists(neumann_file):
    print(f"\n\n")
    analyze_boundary(neumann_file, (400, 441, 92), boundary_layers=10)
    
    # 对比
    print(f"\n{'='*60}")
    print(f"处理前后对比")
    print(f"{'='*60}")
    
    orig_data = np.fromfile(raw_file, dtype=np.uint8).reshape((400, 441, 92))
    neu_data = np.fromfile(neumann_file, dtype=np.uint8).reshape((400, 441, 92))
    
    # 检查边界是否改变
    orig_edge = orig_data[0:3, :, :].mean()
    neu_edge = neu_data[0:3, :, :].mean()
    
    print(f"\n  边界前 3 层平均值:")
    print(f"    原始: {orig_edge:.1f}")
    print(f"    Neumann: {neu_edge:.1f}")
    print(f"    改变: {neu_edge - orig_edge:+.1f}")
else:
    print(f"❌ 找不到 {neumann_file}")
