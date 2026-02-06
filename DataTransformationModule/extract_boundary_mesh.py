"""
从边界 mask 数据生成海洋区域的边界 mesh
这会创建一个不规则的、真实的海洋边界形状
"""

import numpy as np
from skimage import measure
import os

def load_boundary_mask(raw_path, ini_path):
    """加载边界 mask 数据"""
    # 读取配置
    config = {}
    with open(ini_path, 'r') as f:
        for line in f:
            if ':' in line:
                key, val = line.strip().split(':')
                config[key.strip()] = val.strip()
    
    dimx = int(config['dimx'])
    dimy = int(config['dimy'])
    dimz = int(config['dimz'])
    
    # 读取数据
    data = np.fromfile(raw_path, dtype=np.uint8)
    data = data.reshape((dimz, dimx, dimy))
    
    print(f"📦 Loaded boundary mask: {data.shape}")
    print(f"   Value range: {data.min()} - {data.max()}")
    print(f"   Non-zero voxels: {np.count_nonzero(data)}")
    
    return data

def extract_boundary_mesh(mask_data, threshold=128, output_path="ocean_boundary.obj", step_size=4):
    """
    从 mask 数据提取边界表面 mesh
    
    mask 数据中：
    - 高值 (如 255) = 有效海洋区域内部
    - 低值 (如 0) = 边界外部（陆地或无效区域）
    
    我们提取高值区域的外边界作为海洋区域的轮廓
    """
    # 使用 marching cubes 提取等值面
    try:
        verts, faces, normals, values = measure.marching_cubes(
            mask_data.astype(float), 
            level=threshold,
            step_size=step_size  # 降采样以减少顶点数
        )
    except Exception as e:
        print(f"❌ Marching cubes failed: {e}")
        return None
    
    print(f"✅ Extracted boundary surface:")
    print(f"   Vertices: {len(verts)}")
    print(f"   Faces: {len(faces)}")
    
    # 保存为 OBJ
    with open(output_path, 'w') as f:
        f.write("# Ocean boundary mesh\n")
        f.write(f"# Vertices: {len(verts)}, Faces: {len(faces)}\n\n")
        
        # 顶点 - 注意坐标顺序: marching_cubes 返回 (z, x, y)
        for v in verts:
            # 交换坐标使其与数据一致: (z,x,y) -> (x,y,z)
            f.write(f"v {v[1]:.4f} {v[2]:.4f} {v[0]:.4f}\n")
        
        f.write("\n")
        
        # 法线
        for n in normals:
            f.write(f"vn {n[1]:.4f} {n[2]:.4f} {n[0]:.4f}\n")
        
        f.write("\n")
        
        # 面 (OBJ 索引从 1 开始)
        for face in faces:
            f.write(f"f {face[0]+1}//{face[0]+1} {face[1]+1}//{face[1]+1} {face[2]+1}//{face[2]+1}\n")
    
    print(f"💾 Saved to: {output_path}")
    
    # 输出边界信息
    print(f"\n📐 Mesh bounds:")
    print(f"   X: {verts[:,1].min():.1f} - {verts[:,1].max():.1f}")
    print(f"   Y: {verts[:,2].min():.1f} - {verts[:,2].max():.1f}")
    print(f"   Z: {verts[:,0].min():.1f} - {verts[:,0].max():.1f}")
    
    return verts, faces


def main():
    # 路径配置
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 使用 gaussian boundary 数据
    raw_path = os.path.join(base_dir, "MyData", "volume_oxygen_gaussian_boundary.raw")
    ini_path = raw_path + ".ini"
    
    # 输出到 Unity 目录
    output_dir = os.path.join(base_dir, "..", "RenderingModule", "Assets", "WaterMassOutput")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "OceanBoundary.obj")
    
    # 检查文件
    if not os.path.exists(raw_path):
        print(f"❌ Boundary file not found: {raw_path}")
        print("   Trying alternative path...")
        raw_path = os.path.join(base_dir, "..", "RenderingModule", "Assets", "MyData", 
                                "volume_oxygen_gaussian_boundary.raw")
        ini_path = raw_path + ".ini"
    
    if not os.path.exists(raw_path):
        print(f"❌ Cannot find boundary data file")
        return
    
    print("=" * 50)
    print("🌊 Ocean Boundary Mesh Generator")
    print("=" * 50)
    
    # 加载数据
    mask_data = load_boundary_mask(raw_path, ini_path)
    
    # 提取边界 mesh
    # threshold 根据你的 mask 数据调整
    # 如果 mask 是 0/255，用 128
    # 如果 mask 是平滑渐变，可能需要调整
    # step_size=4 会降低分辨率但大幅减少顶点数
    extract_boundary_mesh(mask_data, threshold=100, output_path=output_path, step_size=4)
    
    print("\n✅ Done!")
    print(f"   Import {output_path} into Unity as the ocean boundary reference frame")


if __name__ == "__main__":
    main()
