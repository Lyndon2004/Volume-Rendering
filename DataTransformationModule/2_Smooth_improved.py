# -*- coding: utf-8 -*-
"""
改进版数据平滑脚本
集成了更好的边界处理，避免边界低值问题

主要改进：
1. 使用 Neumann 边界条件处理边界（而非简单设为 0）
2. 智能判断陆地/海洋边界
3. 保留边界的数据完整性和连续性
"""

import pandas as pd
import numpy as np
from tqdm import tqdm
import os
from pyproj import Transformer
import time
import geopandas as gpd
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(__file__)

def neumann_boundary(data_3d, boundary_width=2):
    """
    Neumann 边界条件：用相邻内部值替代边界值
    避免边界的人工低值
    """
    data = data_3d.copy()
    z, x, y = data.shape
    
    # 处理 Z 轴（时间）
    for i in range(boundary_width):
        if i < z:
            data[i, :, :] = data[boundary_width, :, :]
            data[-(i+1), :, :] = data[-(boundary_width+1), :, :]
    
    # 处理 X 轴（空间）
    for i in range(boundary_width):
        if i < x:
            data[:, i, :] = data[:, boundary_width, :]
            data[:, -(i+1), :] = data[:, -(boundary_width+1), :]
    
    # 处理 Y 轴（空间）
    for i in range(boundary_width):
        if i < y:
            data[:, :, i] = data[:, :, boundary_width]
            data[:, :, -(i+1)] = data[:, :, -(boundary_width+1)]
    
    return data


def gaussian_smooth_boundary(data_3d, sigma=1.5, boundary_fade_width=5):
    """
    高斯模糊平滑边界，创建自然的过渡
    """
    blurred = gaussian_filter(data_3d, sigma=sigma)
    
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
    return result


def clipedChinaFrame_improved(data, china_mask_2d, zLength, xLength, yLength, 
                              boundary_method='neumann', clipping_value=1):
    """
    改进的中国地图裁切函数
    
    Args:
        data: 展平的 1D 数据
        china_mask_2d: (xLength, yLength) 的布尔掩膜，True 表示陆地
        zLength, xLength, yLength: 数据维度
        boundary_method: 'neumann', 'gaussian', 或 'none'
        clipping_value: 陆地裁切值（1 而非 0，避免边界过度黑暗）
    
    Returns:
        处理后的展平数据
    """
    temp_res = data.reshape(zLength, xLength, yLength)
    
    # 1. 先应用边界处理
    if boundary_method == 'neumann':
        temp_res = neumann_boundary(temp_res, boundary_width=3)
    elif boundary_method == 'gaussian':
        temp_res = gaussian_smooth_boundary(temp_res, sigma=1.5, boundary_fade_width=5)
    # 否则不处理边界
    
    # 2. 应用地理裁切
    # 创建 3D 掩膜
    china_mask_3d = np.tile(china_mask_2d, (zLength, 1, 1))
    
    # 陆地区域设为 clipping_value（通常为 1）
    temp_res[china_mask_3d] = clipping_value
    
    return temp_res.flatten()


for index in range(0, 8):
    print(f'index:{index + 1}/8')
    interpolateFileName = f"volume_linear_timeWidth_{0 + index * 552}_{0 + (index+1) * 552}_definition_175_175_expand_ratio_2_sill_test"
    importDataPath = os.path.join(HERE, 'InterpolateResult', f'{interpolateFileName}.json')

    pd_test_pred = pd.read_json(importDataPath)
    data = pd_test_pred['data']
    xLength = pd_test_pred['xLength'].values[0]
    yLength = pd_test_pred['yLength'].values[0]
    zLength = pd_test_pred['zLength'].values[0]
    spatial_window_radius = 2
    temporal_window_radius = 24

    if(index != 0):
        prevFileName = f"volume_linear_timeWidth_{0 + (index-1) * 552}_{0 + (index) * 552}_definition_175_175_expand_ratio_2_sill_test"
        prevDataPath = os.path.join(HERE, 'InterpolateResult',  f'{prevFileName}.json')
        prev_pd_test_pred = pd.read_json(prevDataPath)
    if(index != 7):
        nextFileName = f"volume_linear_timeWidth_{0 + (index+1) * 552}_{0 + (index+2) * 552}_definition_175_175_expand_ratio_2_sill_test"
        nextDataPath = os.path.join(HERE, 'InterpolateResult', f'{nextFileName}.json')
        next_pd_test_pred = pd.read_json(nextDataPath)

    def smooth3d_mean(zLength, xLength, yLength):
        _data3d = np.array(data).reshape(zLength, xLength, yLength)
        temp_data = np.array(data).reshape(zLength, xLength, yLength)
        _spatial_window_radius = spatial_window_radius
        _temporal_window_radius = temporal_window_radius
        for t in tqdm(range(zLength)):
            start_t = max(0, t - _temporal_window_radius)
            end_t = min(zLength, t + _temporal_window_radius)
            if(index != 0 and end_t != t + _temporal_window_radius):
                prev_data = np.array(prev_pd_test_pred['data']).reshape(zLength, xLength, yLength)
            if(index != 7 and start_t != t - _temporal_window_radius):
                next_data = np.array(next_pd_test_pred['data']).reshape(zLength, xLength, yLength)
            for x in range(xLength):
                start_x = max(0, x - _spatial_window_radius)
                end_x = min(xLength, x + _spatial_window_radius)
                for y in range(yLength):
                    start_y = max(0, y - _spatial_window_radius)
                    end_y = min(yLength, y + _spatial_window_radius)
                    window = temp_data[start_t:end_t, start_x:end_x, start_y:end_y]
                    if(index != 7 and start_t != t - _temporal_window_radius):
                        window = np.append(window.flatten(), next_data[zLength - temporal_window_radius + t: zLength, start_x:end_x, start_y:end_y].flatten(), axis=0)
                    if(index != 0 and end_t != t + _temporal_window_radius):
                        window = np.append(window.flatten(), prev_data[0: t + _temporal_window_radius - zLength, start_x:end_x, start_y:end_y].flatten(), axis=0)
                    _data3d[t][x][y] = window.mean()
        return _data3d

    def clipedChinaFrame(data):
        # 裁切中国地图
        temp_res = data

        ChinaInCompJsonPath = os.path.join(HERE, 'exampleData', 'chinaChange.json')
        ChinaGeoJsonPath = os.path.join(HERE, 'exampleData', 'chinaGeoJson.json')
        china = gpd.read_file(ChinaInCompJsonPath, crs='EPSG:4326')
        chinaGeoData = gpd.read_file(ChinaGeoJsonPath, crs='EPSG:4326')
        china_total = gpd.GeoSeries([china.iloc[:-1, :].unary_union], crs='EPSG:4326')
        china_total_new = china_total.to_crs(epsg=3857)

        js = chinaGeoData
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        js_box = js.geometry.total_bounds
        js_box[0], js_box[1] = transformer.transform(js_box[0], js_box[1])
        js_box[2], js_box[3] = transformer.transform(js_box[2], js_box[3])
        china = None
        grid_lon_for_clip = np.linspace(js_box[0], js_box[2], xLength)
        grid_lat_for_clip = np.linspace(js_box[1], js_box[3], yLength)
        xgrid, ygrid = np.meshgrid(grid_lon_for_clip, grid_lat_for_clip)

        df_grid = pd.DataFrame(dict(long=xgrid.flatten(), lat=ygrid.flatten()))
        df_grid_geo = gpd.GeoDataFrame(df_grid, geometry=gpd.points_from_xy(df_grid["long"], df_grid["lat"]),
                                    crs='EPSG:3857')
        js_kde_clip = gpd.clip(df_grid_geo, china_total_new)

        js_kde_clip['val'] = False
        df_grid_geo['val'] = True
        df_grid_geo.update(js_kde_clip)

        # 获取布尔掩膜（True = 陆地，False = 海洋）
        china_mask = df_grid_geo['val'].to_numpy().reshape(xLength, yLength)
        
        # 使用改进的裁切函数
        # 选择边界处理方法：
        #   'neumann'  : 用相邻值替代（推荐，最干净）
        #   'gaussian' : 高斯平滑（最平滑）
        #   'none'     : 不处理边界（原始行为）
        temp_res = clipedChinaFrame_improved(
            data,
            china_mask,
            zLength, xLength, yLength,
            boundary_method='neumann',      # ← 改为 'gaussian' 或 'none' 来测试
            clipping_value=1                # ← 改为 0 恢复原始行为
        )

        return temp_res

    # 三维均值滤波
    startTime = time.time()
    smooth_res = smooth3d_mean(zLength, xLength, yLength).reshape(xLength * yLength * zLength)
    timeCost = time.time() - startTime
    print(f'timeCost per timestamp:{timeCost / zLength}')

    smooth_res = clipedChinaFrame(smooth_res)
    smooth_res = np.array(smooth_res)

    def map_values_with_condition(input_array):
        min_value = 1
        max_value = 500

        # 归一化到0~255，注意：1 不再被映射为特殊值，而是正常处理
        mapped_array = np.where(
            input_array == 0, 
            1,  # 只有 0 才映射为 1（完全黑）
            ((input_array - min_value) / (max_value - min_value)) * 249 + 5
        )

        mapped_array = np.round(mapped_array).astype(int)
        return mapped_array

    smooth_res = map_values_with_condition(smooth_res)
    smooth_res = smooth_res.astype(np.uint8)

    ##################################################################
    # 导出

    if(not os.path.exists(os.path.join(HERE, 'UnityRawData'))):
        os.makedirs(os.path.join(HERE, 'UnityRawData'))

    fileName = f'{interpolateFileName}_smooth_s_{spatial_window_radius}_t_{temporal_window_radius}_smooth_correct_improved_boundary.raw'
    outputRawPath = os.path.join(HERE, 'UnityRawData', fileName)
    smooth_res.tofile(outputRawPath)
    
    print(f'x:{xLength}')
    print(f'y:{yLength}')
    print(f'z:{zLength}')

    # 编写并导出配置文件ini
    outputIniPath = os.path.join(HERE, 'UnityRawData', f'{fileName}.ini')
    with open(outputIniPath, 'w') as f:
        ini = f'dimx:{xLength} \n' + f'dimy:{yLength} \n' + f'dimz:{zLength} \n' + 'skip:0 \nformat:uint8'
        f.write(ini)
    
    print(f'✓ 已导出（改进边界处理）: {fileName}')
