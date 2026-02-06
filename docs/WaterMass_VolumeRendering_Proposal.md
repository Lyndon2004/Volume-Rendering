# 水团可视化方案评估：基于 VolumeSTCube 的体积渲染方案

**文档版本**: v1.0  
**创建日期**: 2026-02-05  
**作者**: AI Assistant  
**状态**: 方案评估阶段

---

## 1. 背景与现状

### 1.1 当前方案概述

目前的水团可视化采用 **Mesh 等值面提取方案**：

```
Python (Marching Cubes) → OBJ 文件 → Unity 加载 Mesh → 标准材质渲染
```

**实现组件**:
- `multi_var_processor.py`: 多变量布尔运算，提取等值面
- `MeshSequencePlayer.cs`: 运行时加载 OBJ 序列
- `TrajectoryRenderer.cs`: 质心轨迹渲染
- `OceanBoundaryDisplay.cs`: 海洋边界显示

**当前问题**:
1. **坐标系不一致**: 生成的 mesh 坐标 (0-400, 0-441, 0-92) 与 VolumeSTCube 的归一化坐标 [-0.5, 0.5] 不匹配
2. **旋转问题**: 需要手动应用 90° X 轴旋转
3. **性能隐患**: 11.5 万顶点的边界 mesh，30 帧水团 mesh，内存和渲染开销大
4. **功能有限**: 只能看到表面，无法观察内部结构

### 1.2 VolumeSTCube 渲染原理

VolumeSTCube 使用 **GPU Ray Marching** 进行体积渲染：

```
3D 纹理数据 → GPU Shader → 光线步进采样 → Transfer Function 映射 → 最终颜色
```

**核心特点**:
- 数据存储在 3D 纹理中，坐标归一化到 [0, 1]
- 使用单位立方体 [-0.5, 0.5] 作为渲染容器
- Shader 自动处理光线投射和颜色合成
- 支持切片、裁剪、高亮等交互功能

---

## 2. 新方案：基于 VolumeSTCube 的混合渲染

### 2.1 方案架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Water Mass Tracking System               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────┐    ┌─────────────────────────────┐   │
│   │   Python Backend    │    │      Unity Frontend          │   │
│   │                     │    │                              │   │
│   │  multi_var_mask.py  │───→│  VolumeSTCube 体积渲染      │   │
│   │  (生成 .raw mask)   │    │  + Transfer Function        │   │
│   │                     │    │                              │   │
│   │  trajectory_calc.py │───→│  TrajectoryRenderer         │   │
│   │  (计算质心轨迹)     │    │  (叠加轨迹线)               │   │
│   │                     │    │                              │   │
│   └─────────────────────┘    └─────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流程

```
Step 1: 多变量处理
  chlorophyll.raw ─┐
  NO3.raw ────────┼─→ Boolean Mask ─→ water_mass_mask_t{N}.raw
  salt.raw ───────┘   (0 或 255)

Step 2: 轨迹计算
  water_mass_mask_t*.raw ─→ 质心计算 ─→ trajectory.json

Step 3: Unity 渲染
  water_mass_mask_t{N}.raw ─→ VolumeRenderedObject (体积渲染)
  trajectory.json ─→ LineRenderer (轨迹线)
```

### 2.3 核心组件

| 组件 | 位置 | 功能 |
|------|------|------|
| `WaterMassMaskGenerator.py` | Python | 生成水团 mask 的 .raw 文件 |
| `WaterMassVolumeController.cs` | Unity | 控制体积渲染和时间序列 |
| `WaterMassTransferFunction.cs` | Unity | 专用 TF：mask=1 蓝色，mask=0 透明 |
| `TrajectoryRenderer.cs` | Unity | 保留现有轨迹渲染（需调整坐标系） |

---

## 3. 详细技术方案

### 3.1 Python 端修改

**新脚本: `water_mass_mask_generator.py`**

```python
def generate_water_mass_mask(chloro, no3, salt, logic_expr):
    """
    生成水团布尔 mask
    
    输入: 多个变量的 3D numpy 数组
    输出: uint8 mask (0 或 255)
    """
    # 执行布尔表达式
    mask = eval(logic_expr)  # e.g., "(chloro > 50) & (no3 < 100) & ..."
    
    # 转换为 uint8
    result = np.zeros_like(chloro, dtype=np.uint8)
    result[mask] = 255
    
    return result

def save_as_raw(mask, output_path, dims):
    """
    保存为 VolumeSTCube 兼容的 .raw 格式
    """
    mask.tofile(output_path)
    
    # 生成配套 .ini 文件
    with open(output_path + ".ini", 'w') as f:
        f.write(f"dimx:{dims[0]}\n")
        f.write(f"dimy:{dims[1]}\n")
        f.write(f"dimz:{dims[2]}\n")
        f.write("skip:0\n")
        f.write("format:uint8\n")
```

**轨迹计算 (复用现有逻辑)**:

```python
def calculate_centroid(mask):
    """计算 mask 区域的质心"""
    coords = np.argwhere(mask > 0)
    if len(coords) == 0:
        return None
    centroid = coords.mean(axis=0)
    
    # 归一化到 [0, 1] 以匹配 VolumeSTCube 坐标系
    dims = mask.shape
    normalized = [
        centroid[2] / dims[2],  # X
        centroid[1] / dims[1],  # Y  
        centroid[0] / dims[0],  # Z
    ]
    return normalized
```

### 3.2 Unity 端实现

**`WaterMassVolumeController.cs`**:

```csharp
public class WaterMassVolumeController : MonoBehaviour
{
    [Header("Volume Rendering")]
    public VolumeRenderedObject volumeObject;
    
    [Header("Time Series")]
    public string dataFolder;
    public string filePattern = "water_mass_mask_t{0}.raw";
    public int totalFrames = 30;
    
    [Header("Playback")]
    public float secondsPerFrame = 1.0f;
    public bool autoPlay = true;
    
    private int currentFrame = 0;
    private VolumeDataset[] cachedDatasets;
    
    void Start()
    {
        // 预加载所有帧或按需加载
        PreloadDatasets();
        
        // 设置专用 Transfer Function
        SetupWaterMassTransferFunction();
    }
    
    public void SetFrame(int frameIndex)
    {
        // 切换 3D 纹理
        volumeObject.dataset = cachedDatasets[frameIndex];
        volumeObject.RefreshTextures();
    }
    
    void SetupWaterMassTransferFunction()
    {
        // 创建二值 TF：
        // - 值 = 0 (mask外): 完全透明
        // - 值 = 1 (mask内): 半透明蓝色
        TransferFunction tf = volumeObject.transferFunction;
        tf.colourControlPoints.Clear();
        tf.alphaControlPoints.Clear();
        
        // 透明区域 (0-0.4)
        tf.AddColourControlPoint(0.0f, Color.clear);
        tf.AddAlphaControlPoint(0.0f, 0.0f);
        tf.AddAlphaControlPoint(0.4f, 0.0f);
        
        // 水团区域 (0.5-1.0) - 蓝色半透明
        tf.AddColourControlPoint(0.5f, new Color(0.2f, 0.5f, 0.9f));
        tf.AddAlphaControlPoint(0.5f, 0.3f);
        tf.AddColourControlPoint(1.0f, new Color(0.1f, 0.3f, 0.8f));
        tf.AddAlphaControlPoint(1.0f, 0.6f);
        
        tf.GenerateTexture();
    }
}
```

### 3.3 轨迹线坐标系适配

由于 VolumeSTCube 使用归一化坐标 [-0.5, 0.5]，轨迹点需要转换：

```csharp
// TrajectoryRenderer.cs 修改
Vector3 ConvertToVolumeSpace(Vector3 normalizedCentroid)
{
    // Python 输出: [0, 1] 归一化坐标
    // VolumeSTCube: [-0.5, 0.5] 本地坐标
    return new Vector3(
        normalizedCentroid.x - 0.5f,
        normalizedCentroid.y - 0.5f,
        normalizedCentroid.z - 0.5f
    );
}
```

---

## 4. 方案对比评估

### 4.1 功能对比

| 功能 | 当前 Mesh 方案 | VolumeSTCube 方案 |
|------|---------------|-------------------|
| 表面可视化 | ✅ 原生支持 | ✅ 等值面模式 |
| 内部结构 | ❌ 不支持 | ✅ 透明度渐变 |
| 切片查看 | ❌ 需开发 | ✅ 已有功能 |
| 裁剪框 | ❌ 需开发 | ✅ 已有功能 |
| 高亮区域 | ❌ 需开发 | ✅ 已有功能 |
| Transfer Function | ❌ 固定颜色 | ✅ 完全可定制 |
| 时间序列 | ✅ OBJ 切换 | ✅ 纹理切换 |
| 轨迹线 | ✅ 已实现 | ✅ 可复用 |

### 4.2 性能对比

| 指标 | 当前 Mesh 方案 | VolumeSTCube 方案 |
|------|---------------|-------------------|
| **内存占用** | | |
| - 单帧数据 | ~5-20 MB (OBJ) | ~15 MB (.raw) |
| - 30 帧总计 | ~150-600 MB | ~450 MB (或流式加载) |
| - 边界 mesh | ~11 MB | 不需要 |
| **渲染性能** | | |
| - CPU 负载 | 高 (mesh 管理) | 低 |
| - GPU 负载 | 中 (标准渲染) | 中-高 (ray marching) |
| - 帧率 (预估) | 30-60 FPS | 60+ FPS |
| **加载时间** | | |
| - 首帧 | 慢 (解析 OBJ) | 快 (二进制读取) |
| - 切换帧 | 中 | 快 |

### 4.3 开发成本对比

| 工作项 | 当前方案 (已完成) | VolumeSTCube 方案 (待开发) |
|--------|------------------|---------------------------|
| Python 数据处理 | ✅ 90% | 需修改 ~20% |
| Unity 渲染组件 | ✅ 70% | 需开发 ~40% |
| 坐标系统适配 | ⚠️ 有问题 | 需重新设计 |
| 时间序列播放 | ✅ 已完成 | 可复用 70% |
| 轨迹渲染 | ✅ 已完成 | 需坐标适配 |
| UI 集成 | ❌ 未开始 | 可复用现有 VolumeSTCube UI |

### 4.4 优缺点总结

**VolumeSTCube 方案优点**:

1. ✅ **渲染质量高**: 体积渲染可显示内部浓度分布
2. ✅ **性能好**: GPU 加速，适合大数据集
3. ✅ **功能丰富**: 复用切片、裁剪、TF 等现有功能
4. ✅ **坐标系统一**: 与现有海洋数据渲染保持一致
5. ✅ **可扩展性强**: 易于添加新的可视化效果

**VolumeSTCube 方案缺点**:

1. ⚠️ **内存占用**: 需要加载完整 3D 纹理（但可优化）
2. ⚠️ **开发工作**: 需要新的集成代码
3. ⚠️ **学习曲线**: 需要理解现有 VolumeSTCube 架构
4. ⚠️ **边界模糊**: 布尔 mask 的硬边界在体积渲染中可能不够清晰

---

## 5. 风险评估

### 5.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 3D 纹理过大导致崩溃 | 中 | 高 | 下采样或分块加载 |
| TF 难以准确表达二值 mask | 低 | 中 | 调整 TF 参数或使用等值面模式 |
| 时间序列切换卡顿 | 中 | 中 | 预加载或异步加载 |
| 轨迹线与体积不对齐 | 低 | 低 | 仔细验证坐标转换 |

### 5.2 进度风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| VolumeSTCube API 变更 | 低 | 中 | 使用稳定的公开接口 |
| 调试周期超预期 | 中 | 中 | 分阶段测试，快速迭代 |

---

## 6. 实施计划

### Phase 1: 概念验证 (POC) - 1-2 天

1. **目标**: 验证单帧 mask 能否用 VolumeSTCube 正确渲染
2. **任务**:
   - 修改 Python 输出单帧 mask.raw
   - 手动导入 Unity，验证渲染效果
   - 测试 Transfer Function 配置

### Phase 2: 核心功能 - 2-3 天

1. **目标**: 完成时间序列播放
2. **任务**:
   - 开发 `WaterMassVolumeController.cs`
   - 实现帧切换逻辑
   - 优化加载性能

### Phase 3: 集成与优化 - 1-2 天

1. **目标**: 集成轨迹线，优化体验
2. **任务**:
   - 适配 TrajectoryRenderer 坐标系
   - 添加 UI 控件
   - 性能调优

---

## 7. 建议与决策

### 7.1 推荐方案

**推荐采用 VolumeSTCube 方案**，理由：

1. **长期收益大于短期成本**: 虽然需要重构，但获得的功能和性能提升显著
2. **代码统一**: 与现有海洋数据渲染架构保持一致，便于维护
3. **用户体验**: 海洋学家可以使用熟悉的 VolumeSTCube 交互方式
4. **可扩展性**: 未来添加更多变量或可视化效果更容易

### 7.2 保留选项

如果时间紧迫，可以先 **修复当前 Mesh 方案的坐标问题**：
- 在 Python 中归一化 mesh 坐标到 [-0.5, 0.5]
- 调整 Unity 端的偏移和旋转
- 作为临时方案使用

### 7.3 下一步行动

请确认：
1. 是否同意采用 VolumeSTCube 方案？
2. 是否先进行 Phase 1 POC 验证？
3. 对时间表是否有要求？

---

## 附录 A: 相关文件

| 文件 | 说明 |
|------|------|
| `DataTransformationModule/multi_var_processor.py` | 当前多变量处理器 |
| `RenderingModule/Assets/Scripts/WaterMass/` | 当前水团渲染组件 |
| `RenderingModule/Assets/Scripts/VolumeObject/` | VolumeSTCube 核心组件 |
| `RenderingModule/Assets/Shaders/DirectVolumeRenderingShader.shader` | 体积渲染着色器 |

## 附录 B: 参考资料

- [VolumeSTCube 架构分析](./VolumeRendering_Improvement_Guide.md)
- [Unity Volume Rendering](https://github.com/mlavik1/UnityVolumeRendering)
- [Marching Cubes vs Ray Marching](https://en.wikipedia.org/wiki/Volume_rendering)
