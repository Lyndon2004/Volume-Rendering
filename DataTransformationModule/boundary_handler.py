# -*- coding: utf-8 -*-
"""
改进的海洋数据边界处理模块
用于替代或补充 2_Smooth.py 中的 clipedChinaFrame 函数

三种边界处理策略：
1. Neumann 边界条件：边界用相邻值替代
2. 高斯模糊平滑：边界逐渐过渡
3. 反射填充：镜像复制内部数据到边界
"""

import numpy as np
from scipy import ndimage
from scipy.ndimage import gaussian_filter


class BoundaryHandler:
    """海洋数据边界处理类"""
    
    @staticmethod
    def neumann_boundary(data_3d, boundary_width=2):
        """
        Neumann 边界条件：用相邻内部值替代边界
        
        原理：边界处的梯度为 0，所以边界值 = 相邻内部值
        适用：海洋数据，避免人工低值
        
        Args:
            data_3d: (Z, X, Y) 的 3D 数据
            boundary_width: 边界宽度（像素数）
        
        Returns:
            处理后的 3D 数据
        """
        data = data_3d.copy()
        z, x, y = data.shape
        
        # 处理前后面（Z 轴）
        for i in range(boundary_width):
            if i < z:
                data[i, :, :] = data[boundary_width, :, :]     # 前面用内层替代
                data[-(i+1), :, :] = data[-(boundary_width+1), :, :]  # 后面用内层替代
        
        # 处理左右面（X 轴）
        for i in range(boundary_width):
            if i < x:
                data[:, i, :] = data[:, boundary_width, :]     # 左面
                data[:, -(i+1), :] = data[:, -(boundary_width+1), :]  # 右面
        
        # 处理上下面（Y 轴）
        for i in range(boundary_width):
            if i < y:
                data[:, :, i] = data[:, :, boundary_width]     # 上面
                data[:, :, -(i+1)] = data[:, :, -(boundary_width+1)]  # 下面
        
        return data
    
    @staticmethod
    def gaussian_smooth_boundary(data_3d, sigma=1.5, boundary_fade_width=5):
        """
        高斯模糊平滑边界
        
        原理：对边界附近区域应用高斯模糊，创建平滑的过渡
        适用：需要自然过渡的场景
        
        Args:
            data_3d: (Z, X, Y) 的 3D 数据
            sigma: 高斯模糊的标准差
            boundary_fade_width: 边界淡出宽度
        
        Returns:
            处理后的 3D 数据
        """
        # 先对整个数据应用高斯模糊
        blurred = gaussian_filter(data_3d, sigma=sigma)
        
        # 创建边界淡出掩膜
        z, x, y = data_3d.shape
        mask = np.ones_like(data_3d, dtype=float)
        
        # 在边界附近逐渐从 1 变成 0
        for i in range(boundary_fade_width):
            fade = (boundary_fade_width - i) / boundary_fade_width
            
            mask[i, :, :] *= fade
            mask[-(i+1), :, :] *= fade
            mask[:, i, :] *= fade
            mask[:, -(i+1), :] *= fade
            mask[:, :, i] *= fade
            mask[:, :, -(i+1)] *= fade
        
        # 在边界用模糊版本混合，内部用原始数据
        result = data_3d * mask + blurred * (1 - mask)
        
        return result
    
    @staticmethod
    def reflect_boundary(data_3d, boundary_width=3):
        """
        反射填充边界
        
        原理：用镜像的内部数据填充边界，保持数据连续性
        适用：周期性或对称数据
        
        Args:
            data_3d: (Z, X, Y) 的 3D 数据
            boundary_width: 边界宽度
        
        Returns:
            处理后的 3D 数据
        """
        data = data_3d.copy()
        z, x, y = data.shape
        
        # 创建带边界的数据副本
        padded = np.pad(data, 
                       ((boundary_width, boundary_width), 
                        (boundary_width, boundary_width), 
                        (boundary_width, boundary_width)), 
                       mode='reflect')
        
        # 提取反射后的完整数据
        result = padded[boundary_width:boundary_width+z,
                       boundary_width:boundary_width+x,
                       boundary_width:boundary_width+y]
        
        return result
    
    @staticmethod
    def selective_boundary_fill(data_3d, mask, boundary_width=3, method='neumann'):
        """
        选择性边界填充
        
        原理：根据地理掩膜（陆地/海洋），智能处理边界
        - 陆地边界：用 Neumann 或高斯平滑
        - 海洋内部：保留原始值
        
        Args:
            data_3d: (Z, X, Y) 的 3D 数据
            mask: (X, Y) 的布尔掩膜，True 表示有效海洋区域
            boundary_width: 边界宽度
            method: 'neumann' 或 'gaussian' 或 'reflect'
        
        Returns:
            处理后的 3D 数据
        """
        data = data_3d.copy()
        z, x, y = data.shape
        
        # 扩展掩膜到 3D
        mask_3d = np.tile(mask, (z, 1, 1))
        
        if method == 'neumann':
            processed = BoundaryHandler.neumann_boundary(data, boundary_width)
        elif method == 'gaussian':
            processed = BoundaryHandler.gaussian_smooth_boundary(data, boundary_fade_width=boundary_width)
        elif method == 'reflect':
            processed = BoundaryHandler.reflect_boundary(data, boundary_width)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # 在边界附近混合：边界用处理版本，内部用原始版本
        distance_to_edge = np.minimum(
            np.minimum(
                np.arange(x)[np.newaxis, :, np.newaxis],
                (x - 1 - np.arange(x))[np.newaxis, :, np.newaxis]
            ),
            np.minimum(
                np.arange(y)[np.newaxis, np.newaxis, :],
                (y - 1 - np.arange(y))[np.newaxis, np.newaxis, :]
            )
        )
        
        # 创建淡出因子（靠近边界时为 0，内部为 1）
        blend_factor = np.clip(distance_to_edge / boundary_width, 0, 1)
        blend_factor_3d = np.tile(blend_factor, (z, 1, 1))
        
        # 混合
        result = data * blend_factor_3d + processed * (1 - blend_factor_3d)
        
        return result


def apply_improved_boundary_handling(data_3d, china_mask_2d, method='neumann', 
                                    boundary_width=3, clipping_value=1):
    """
    改进的边界处理流程
    
    替代原来的 clipedChinaFrame 函数
    
    Args:
        data_3d: (Z, X, Y) 的原始 3D 数据
        china_mask_2d: (X, Y) 的布尔掩膜，True 表示陆地，False 表示海洋
        method: 边界处理方法 ('neumann', 'gaussian', 'reflect', 'selective')
        boundary_width: 边界处理宽度
        clipping_value: 陆地裁切值（默认 0，表示完全裁切；改为 1 保留边界）
    
    Returns:
        处理后的 3D 数据
    """
    data = data_3d.copy()
    z, x, y = data.shape
    
    # 1. 首先应用边界处理
    if method == 'selective':
        # 选择性处理：在海洋边界用插值，陆地边界用标记值
        ocean_mask = ~china_mask_2d  # 反转掩膜：False 变成 True
        data = BoundaryHandler.selective_boundary_fill(
            data, ocean_mask, boundary_width=boundary_width, method='neumann'
        )
    else:
        # 全局边界处理
        data = {
            'neumann': BoundaryHandler.neumann_boundary,
            'gaussian': BoundaryHandler.gaussian_smooth_boundary,
            'reflect': BoundaryHandler.reflect_boundary
        }[method](data, boundary_width)
    
    # 2. 然后应用地理裁切（陆地设为标记值，而非 0）
    mask_3d = np.tile(china_mask_2d, (z, 1, 1))
    data[mask_3d] = clipping_value
    
    return data


# ============================================================================
# 使用示例（集成到 2_Smooth.py 中）
# ============================================================================

"""
在 2_Smooth.py 中的使用方式：

# 原来的代码：
# temp_res[np.tile(df_grid_geo['val'].to_numpy(), (zLength)).tolist()] = 0.0
# return temp_res

# 改成：

def clipedChinaFrame_improved(data, china_mask):
    '''改进版本：更好的边界处理'''
    # data: 展平的 1D 数组
    # 转换为 3D
    data_3d = data.reshape(zLength, xLength, yLength)
    
    # 应用改进的边界处理
    # 选择以下任意一种方法：
    
    # 方法 A：Neumann 边界 + 智能陆地标记（推荐）
    data_3d = apply_improved_boundary_handling(
        data_3d, 
        china_mask, 
        method='selective',
        boundary_width=3,
        clipping_value=1  # 改为 1，边界不会过度黑暗
    )
    
    # 方法 B：纯高斯平滑（最平滑）
    # data_3d = apply_improved_boundary_handling(
    #     data_3d,
    #     china_mask,
    #     method='gaussian',
    #     boundary_width=5,
    #     clipping_value=0
    # )
    
    # 方法 C：反射填充（最保持数据完整性）
    # data_3d = apply_improved_boundary_handling(
    #     data_3d,
    #     china_mask,
    #     method='reflect',
    #     boundary_width=3,
    #     clipping_value=0
    # )
    
    return data_3d.flatten()
"""
