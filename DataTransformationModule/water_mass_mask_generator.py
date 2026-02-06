"""
Phase 1 POC: 水团 Mask 生成器
将多变量布尔运算结果输出为 VolumeSTCube 兼容的 .raw 格式

输出:
- water_mass_mask_t{N}.raw: 水团区域 mask (0 或 255)
- water_mass_mask_t{N}.raw.ini: 维度配置文件
- water_mass_trajectory.json: 质心轨迹（归一化坐标）
"""

import os
import glob
import re
import json
import numpy as np

# 复用现有的 volume_loader
try:
    from volume_loader import load_volume_from_ini
except ImportError:
    from DataTransformationModule.volume_loader import load_volume_from_ini


def extract_time_index(filename):
    """从文件名提取时间索引"""
    match = re.search(r'time_(\d+)', filename)
    if match:
        return int(match.group(1))
    return -1


class WaterMassMaskGenerator:
    """
    水团 Mask 生成器
    将多变量布尔运算结果输出为 VolumeSTCube 兼容格式
    """
    
    def __init__(self, data_root):
        self.data_root = data_root
        self.data_sources = {}  # {var_name: {time_idx: file_path}}
        self.dims = None  # (dimz, dimy, dimx)
    
    def register_variable(self, var_name, filename_pattern):
        """注册数据变量"""
        search_path = os.path.join(self.data_root, filename_pattern)
        files = glob.glob(search_path)
        
        if not files:
            print(f"⚠️ Warning: No files found for '{var_name}' with pattern '{search_path}'")
            return
        
        self.data_sources[var_name] = {}
        
        for f in files:
            t_idx = extract_time_index(os.path.basename(f))
            if t_idx != -1:
                self.data_sources[var_name][t_idx] = f
        
        print(f"✅ Registered '{var_name}': {len(self.data_sources[var_name])} time steps")
    
    def get_common_time_indices(self):
        """获取所有变量共有的时间索引"""
        if not self.data_sources:
            return []
        
        all_times = [set(v.keys()) for v in self.data_sources.values()]
        common = set.intersection(*all_times)
        return sorted(common)
    
    def load_frame(self, time_idx):
        """加载指定时间步的所有变量"""
        frame_data = {}
        
        for var_name, time_files in self.data_sources.items():
            if time_idx not in time_files:
                print(f"⚠️ Missing {var_name} at time {time_idx}")
                continue
            
            ini_path = time_files[time_idx]
            volume, meta = load_volume_from_ini(ini_path)
            frame_data[var_name] = volume
            
            # 记录维度
            if self.dims is None:
                self.dims = volume.shape
                print(f"📐 Data dimensions: {self.dims} (Z, Y, X)")
        
        return frame_data
    
    def evaluate_logic(self, frame_data, logic_expr):
        """
        执行布尔逻辑表达式
        
        Args:
            frame_data: {var_name: 3D numpy array}
            logic_expr: 如 "(chloro > 50) & (no3 < 100) & (salt > 30)"
        
        Returns:
            布尔 mask 数组
        """
        # 将变量名映射到实际数据
        local_vars = frame_data.copy()
        
        # 执行表达式
        try:
            mask = eval(logic_expr, {"__builtins__": {}}, local_vars)
        except Exception as e:
            print(f"❌ Logic evaluation error: {e}")
            return None
        
        return mask
    
    def calculate_centroid(self, mask):
        """
        计算 mask 区域的质心
        
        Returns:
            归一化坐标 [x, y, z] 范围 [0, 1]，或 None
        """
        coords = np.argwhere(mask)
        if len(coords) == 0:
            return None, 0
        
        # coords 的顺序是 (z, y, x)
        centroid = coords.mean(axis=0)
        volume_voxels = len(coords)
        
        # 归一化到 [0, 1]
        # 注意坐标顺序转换: numpy (z,y,x) -> 标准 (x,y,z)
        dims = mask.shape  # (Z, Y, X)
        normalized = [
            float(centroid[2] / dims[2]),  # X
            float(centroid[1] / dims[1]),  # Y
            float(centroid[0] / dims[0]),  # Z
        ]
        
        return normalized, volume_voxels
    
    def save_mask_raw(self, mask, output_path):
        """
        保存 mask 为 .raw 文件
        
        mask 中 True 保存为 255，False 保存为 0
        """
        # 转换为 uint8
        raw_data = np.zeros(mask.shape, dtype=np.uint8)
        raw_data[mask] = 255
        
        # 保存二进制数据
        raw_data.tofile(output_path)
        
        # 生成配套 .ini 文件
        ini_path = output_path + ".ini"
        dims = mask.shape  # (Z, Y, X)
        with open(ini_path, 'w') as f:
            f.write(f"dimx:{dims[2]}\n")
            f.write(f"dimy:{dims[1]}\n")
            f.write(f"dimz:{dims[0]}\n")
            f.write("skip:0\n")
            f.write("format:uint8\n")
        
        return output_path, ini_path
    
    def process_sequence(self, output_dir, logic_expr, prefix="water_mass_mask"):
        """
        处理完整时间序列
        
        Args:
            output_dir: 输出目录
            logic_expr: 布尔逻辑表达式
            prefix: 输出文件前缀
        """
        os.makedirs(output_dir, exist_ok=True)
        
        time_indices = self.get_common_time_indices()
        if not time_indices:
            print("❌ No common time indices found!")
            return
        
        print(f"\n🚀 Processing {len(time_indices)} time steps...")
        print(f"📝 Logic: {logic_expr}\n")
        
        trajectory = []
        
        for i, t_idx in enumerate(time_indices):
            print(f"[{i+1}/{len(time_indices)}] Processing time {t_idx}...")
            
            # 1. 加载数据
            frame_data = self.load_frame(t_idx)
            if not frame_data:
                continue
            
            # 2. 执行布尔逻辑
            mask = self.evaluate_logic(frame_data, logic_expr)
            if mask is None:
                continue
            
            # 3. 计算质心
            centroid, volume = self.calculate_centroid(mask)
            
            # 4. 保存 .raw 文件
            raw_filename = f"{prefix}_t{t_idx}.raw"
            raw_path = os.path.join(output_dir, raw_filename)
            self.save_mask_raw(mask, raw_path)
            
            # 5. 记录轨迹
            trajectory.append({
                "time_index": t_idx,
                "centroid": centroid,  # 归一化坐标 [0,1]
                "volume_voxels": volume,
                "raw_file": raw_filename
            })
            
            voxel_count = np.count_nonzero(mask)
            print(f"    ✅ Saved {raw_filename} ({voxel_count} voxels)")
        
        # 6. 保存轨迹 JSON
        traj_path = os.path.join(output_dir, f"{prefix}_trajectory.json")
        with open(traj_path, 'w') as f:
            json.dump(trajectory, f, indent=2)
        
        print(f"\n✅ Done! Generated {len(trajectory)} frames")
        print(f"📁 Output: {output_dir}")
        print(f"📍 Trajectory: {traj_path}")
        
        # 输出统计信息
        if trajectory:
            volumes = [t['volume_voxels'] for t in trajectory if t['volume_voxels'] > 0]
            if volumes:
                print(f"\n📊 Statistics:")
                print(f"   Volume range: {min(volumes)} - {max(volumes)} voxels")
                print(f"   Average: {np.mean(volumes):.0f} voxels")


def main():
    """POC 测试入口"""
    
    # 配置路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 数据源目录 (Unity 项目中的 MyData)
    DATA_ROOT = os.path.join(script_dir, "..", "RenderingModule", "Assets", "MyData")
    
    # 输出目录
    OUTPUT_DIR = os.path.join(script_dir, "..", "RenderingModule", "Assets", "WaterMassMasks")
    
    print("=" * 60)
    print("🌊 Water Mass Mask Generator - POC Phase 1")
    print("=" * 60)
    print(f"📂 Data root: {DATA_ROOT}")
    print(f"📂 Output dir: {OUTPUT_DIR}")
    print()
    
    # 创建生成器
    generator = WaterMassMaskGenerator(DATA_ROOT)
    
    # 注册变量
    generator.register_variable("chloro", "chlorophyll/*chlorophyll*.raw.ini")
    generator.register_variable("no3", "NO3/*NO3*.raw.ini")
    generator.register_variable("salt", "salt/*salt*.raw.ini")
    
    # 定义水团逻辑
    # 高叶绿素 + 低硝酸盐 + 中等盐度
    logic = "(chloro > 50) & (no3 < 100) & (salt > 30) & (salt < 200)"
    
    # 执行处理
    generator.process_sequence(OUTPUT_DIR, logic, prefix="water_mass_mask")
    
    print("\n" + "=" * 60)
    print("🎯 Next Steps:")
    print("   1. Open Unity, go to: Assets/WaterMassMasks/")
    print("   2. Import any .raw file using VolumeSTCube importer")
    print("   3. Set Transfer Function: 0=transparent, 255=blue")
    print("   4. Verify the water mass region is correctly displayed")
    print("=" * 60)


if __name__ == "__main__":
    main()
