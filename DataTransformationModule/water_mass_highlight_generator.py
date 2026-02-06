#!/usr/bin/env python3
"""
Water Mass Highlighted Volume Generator
生成带上下文的水团高亮体积数据

输出格式：
- 水团外区域：原始数据值 × 0.5 (范围 0-127)
- 水团内区域：原始数据值 × 0.5 + 128 (范围 128-255)

这样 Transfer Function 可以区分：
- 0-127：背景数据（半透明，看到整体结构）
- 128-255：水团区域（高亮，突出显示）
"""

import numpy as np
import json
import os
from pathlib import Path

# 复用现有的 volume_loader
from volume_loader import load_volume_from_ini


def load_volume_with_metadata(raw_path):
    """加载 .raw 文件，自动查找对应的 .ini"""
    ini_path = raw_path + ".ini"
    if not os.path.exists(ini_path):
        # 尝试其他命名方式
        ini_path = raw_path.replace('.raw', '.ini')
    return load_volume_from_ini(ini_path)


class WaterMassHighlightGenerator:
    """生成带背景上下文的水团高亮体积"""
    
    def __init__(self):
        self.variables = {}  # {name: 3D numpy array}
        self.shape = None
        self.logic_expr = None
        
    def register_variable(self, name: str, volume: np.ndarray):
        """注册变量（如 chloro, no3, salt, oxygen）"""
        if self.shape is None:
            self.shape = volume.shape
        else:
            assert volume.shape == self.shape, f"Shape mismatch: {volume.shape} vs {self.shape}"
        self.variables[name] = volume.astype(np.float32)
        print(f"  📊 Registered '{name}': shape={volume.shape}, range=[{volume.min():.1f}, {volume.max():.1f}]")
        
    def set_logic(self, expr: str):
        """设置水团定义逻辑，如 '(chloro > 50) & (no3 < 100) & (salt > 30) & (salt < 200)'"""
        self.logic_expr = expr
        print(f"  🔬 Logic: {expr}")
        
    def evaluate_mask(self) -> np.ndarray:
        """计算水团 mask (布尔数组)"""
        # 将变量名映射到局部变量
        local_vars = {name: arr for name, arr in self.variables.items()}
        mask = eval(self.logic_expr, {"__builtins__": {}}, local_vars)
        return mask.astype(bool)
    
    def generate_highlighted_volume(self, display_var: str = 'oxygen') -> np.ndarray:
        """
        生成高亮体积 - 保持原始数据结构，只增强水团区域
        
        策略：
        - 保持原始数据不变
        - 水团区域的值提升到更高范围（更亮）
        
        Returns:
            uint8 volume: 原始结构 + 水团高亮
        """
        if display_var not in self.variables:
            raise ValueError(f"Display variable '{display_var}' not registered")
            
        # 获取显示变量（原始数据）
        display_data = self.variables[display_var].copy()
        
        # 计算水团 mask（只在有效数据区域）
        valid_mask = display_data > 0
        water_mass_mask = self.evaluate_mask() & valid_mask
        
        # 创建输出：直接复制原始数据
        output = display_data.copy()
        
        # 水团区域：将值提升到高范围 (200-255)
        # 这样用原始 TF 也能看到高亮效果
        if np.any(water_mass_mask):
            water_values = display_data[water_mass_mask]
            # 归一化到 200-255 范围
            wmin, wmax = water_values.min(), water_values.max()
            if wmax > wmin:
                normalized = (water_values - wmin) / (wmax - wmin)
                output[water_mass_mask] = (normalized * 55 + 200).astype(np.uint8)
            else:
                output[water_mass_mask] = 230
        
        return output.astype(np.uint8), water_mass_mask
    
    def calculate_centroid(self, mask: np.ndarray) -> tuple:
        """计算水团质心（归一化坐标 0-1）"""
        indices = np.where(mask)
        if len(indices[0]) == 0:
            return None, 0
            
        centroid = [
            float(np.mean(indices[0])) / self.shape[0],  # x normalized
            float(np.mean(indices[1])) / self.shape[1],  # y normalized  
            float(np.mean(indices[2])) / self.shape[2],  # z normalized
        ]
        volume = int(np.sum(mask))
        return centroid, volume
    
    def save_volume(self, volume: np.ndarray, filepath: str):
        """保存 .raw 和 .raw.ini"""
        # 保存 raw - 注意：volume 的 shape 是 (dimz, dimy, dimx)
        # 但 ini 需要写成 dimx, dimy, dimz 的顺序
        volume.tofile(filepath)
        
        # 保存 ini - 维度顺序要和原始数据一致
        # self.shape = (dimz, dimy, dimx)，所以要反过来写
        dimz, dimy, dimx = self.shape
        ini_content = f"dimx:{dimx}\ndimy:{dimy}\ndimz:{dimz}\nskip:0\nformat:uint8\n"
        with open(filepath + ".ini", 'w') as f:
            f.write(ini_content)
            
    def process_time_series(self, data_dir: str, output_dir: str, 
                           time_range: range, display_var: str = 'oxygen'):
        """
        处理时间序列（单目录模式）
        """
        # 转发到多目录模式
        return self.process_time_series_multidir(data_dir, output_dir, time_range, display_var)
    
    def process_time_series_multidir(self, base_dir: str, output_dir: str, 
                                      time_range, display_var: str = 'chloro'):
        """
        处理时间序列（多目录模式）
        
        数据目录结构:
        base_dir/
            chlorophyll/volume_chlorophyll_data_time_X_255.raw
            NO3/volume_NO3_data_time_X_255.raw
            salt/volume_salt_data_time_X_255.raw
        
        Args:
            base_dir: 基础目录
            output_dir: 输出目录  
            time_range: 时间帧列表
            display_var: 用于显示的主变量
        """
        os.makedirs(output_dir, exist_ok=True)
        trajectory = []
        
        print(f"\n🌊 Processing {len(time_range)} frames...")
        print(f"   Display variable: {display_var}")
        print(f"   Output: Highlighted volume (0-127: background, 128-255: water mass)\n")
        
        for t in time_range:
            print(f"⏱️  Frame {t}:")
            self.variables.clear()
            self.shape = None
            
            # 多目录数据配置
            var_configs = [
                ('chloro', 'chlorophyll', f'volume_chlorophyll_data_time_{t}_255.raw'),
                ('no3', 'NO3', f'volume_NO3_data_time_{t}_255.raw'),
                ('salt', 'salt', f'volume_salt_data_time_{t}_255.raw'),
            ]
            
            all_loaded = True
            for var_name, subdir, filename in var_configs:
                filepath = os.path.join(base_dir, subdir, filename)
                if os.path.exists(filepath):
                    vol, meta = load_volume_with_metadata(filepath)
                    self.register_variable(var_name, vol)
                else:
                    print(f"  ⚠️  Missing: {subdir}/{filename}")
                    all_loaded = False
                    
            if not all_loaded:
                print(f"  ⏭️  Skipping frame {t} due to missing data")
                continue
                
            # 生成高亮体积
            highlighted_vol, mask = self.generate_highlighted_volume(display_var)
            
            # 计算质心和体积
            centroid, vol_size = self.calculate_centroid(mask)
            
            # 统计
            water_mass_voxels = np.sum(mask)
            background_voxels = np.sum(~mask)
            print(f"  📈 Background: {background_voxels:,} voxels (0-127)")
            print(f"  🎯 Water Mass: {water_mass_voxels:,} voxels (128-255)")
            
            # 保存
            output_file = os.path.join(output_dir, f"water_mass_highlighted_t{t}.raw")
            self.save_volume(highlighted_vol, output_file)
            print(f"  💾 Saved: {output_file}")
            
            # 记录轨迹
            if centroid:
                trajectory.append({
                    'time_index': t,
                    'centroid': centroid,
                    'volume_voxels': vol_size,
                    'raw_file': f"water_mass_highlighted_t{t}.raw"
                })
        
        # 保存轨迹
        traj_file = os.path.join(output_dir, "water_mass_trajectory.json")
        with open(traj_file, 'w') as f:
            json.dump(trajectory, f, indent=2)
        print(f"\n📍 Trajectory saved: {traj_file}")
        
        return trajectory


def main():
    """主函数：生成带高亮的水团体积数据"""
    
    # 配置 - 数据在 Unity 项目的 Assets/MyData 下
    BASE_DIR = "/Users/yiquan/Desktop/VolumeSTCube/RenderingModule/Assets/MyData"
    OUTPUT_DIR = "/Users/yiquan/Desktop/VolumeSTCube/RenderingModule/Assets/WaterMassHighlighted"
    
    generator = WaterMassHighlightGenerator()
    
    # 设置水团定义逻辑
    generator.set_logic("(chloro > 50) & (no3 < 100) & (salt > 30) & (salt < 200)")
    
    # 检查有哪些时间帧可用（以 chlorophyll 为基准）
    chloro_dir = os.path.join(BASE_DIR, "chlorophyll")
    available_times = []
    for t in range(30):
        test_file = os.path.join(chloro_dir, f"volume_chlorophyll_data_time_{t}_255.raw")
        if os.path.exists(test_file):
            available_times.append(t)
    
    print(f"📂 Found {len(available_times)} available time frames")
    
    if not available_times:
        print("❌ No data files found!")
        return
        
    # 处理所有可用帧
    trajectory = generator.process_time_series_multidir(
        base_dir=BASE_DIR,
        output_dir=OUTPUT_DIR,
        time_range=available_times,
        display_var='chloro'  # 使用叶绿素作为显示变量（数据更完整）
    )
    
    print(f"\n✅ Done! Generated {len(trajectory)} highlighted volume frames")
    print(f"   Value encoding:")
    print(f"   - 0-127:   Background (original data, semi-transparent)")
    print(f"   - 128-255: Water Mass (highlighted, bright color)")


if __name__ == "__main__":
    main()
