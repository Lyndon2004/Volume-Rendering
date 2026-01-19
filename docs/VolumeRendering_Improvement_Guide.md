# 海洋含氧量体渲染可视化改进指南

> 更新（基于你的当前参数）：你现在的设置为 Base=1、Internal=0.1、Edge=0。该组合的有效不透明度为“TF Alpha × 0.1”（因为 Edge=0 时不透明度调制等于 Base，而随后还会乘以 Internal）。在 400×441×92 的小数据上，这通常偏透明。建议先将 Internal 提升到 0.6–1.0，再根据需要微调 Base 与（可选）最小梯度。

## 快速处方（小数据 + 内部观察）

### 现状评估（Base=1, Internal=0.1, Edge=0）
- 结果：等效 α = TF α × 0.1，整体偏透明，细节累积不足。
- 适用：仅在 TF α 非常陡峭且总体偏高时可接受；对海洋含氧量这种平滑场不理想。

### 预设 A：高可见度（先摆脱“雾态”）
- BaseDensityAlpha: 0.8–1.0（保留平坦区存在感）
- InternalDensityScale: 0.8–1.0（小数据可承受更高累积）
- EdgeContribution: 0（含义弱、避免描边）
- MinGradient: 任意（Edge=0 时对不透明度无影响；用于光照时可设 0.001–0.003）
- 何时用：快速确认整体层次与分布，适合内部沉浸式浏览。

### 预设 B：均衡质感（在可见基础上略提边界）
- BaseDensityAlpha: 0.6
- InternalDensityScale: 0.6
- EdgeContribution: 0.2（极轻的梯度驱动，不改变语义）
- MinGradient: 0.003（与轻量 Edge 搭配，避免过度突兀）
- 何时用：想要轻微强调过渡带，又不抢夺密度语义时。

### 5 分钟 A/B 验证清单
- 在材质 Inspector 里直接切 A/B 两套数值，对比：
    - 是否仍然“过透明”？→ 提高 InternalDensityScale。
    - 平坦区域是否“糊一片”？→ 提高 BaseDensityAlpha。
    - 若层次单薄 → 打开 LIGHTING_ON（仅用于立体感，Edge 可继续为 0）。
- 小数据建议将 raymarch 步数提高到 ≥1024（若有开关，内部观察时开启）。

## 目录
1. [问题诊断](#问题诊断)
2. [短期改进：调参数](#短期改进调参数)
3. [中期改进：改 Shader](#中期改进改-shader)
4. [长期改进：架构重构](#长期改进架构重构)
5. [工程化实现优先级](#工程化实现优先级)

---

## 问题诊断

### 当前系统的核心矛盾

你的系统**复用了 VolumeSTCube 的 Raymarching 框架**，这个框架原本设计用于：
- 医学影像（CT/MRI）的**外部观察**
- 具有**明显梯度变化**的数据（如骨骼-软组织边界）
- **等值面提取**和**边缘检测**

而你的需求是：
- 海洋含氧量数据的**内部沉浸式观察**
- 数据相对**平滑连续**，梯度变化不剧烈
- 需要表达**定量语义**（缺氧/适氧/富氧区）

**这导致了根本性的不匹配。**

---

## 短期改进：调参数

### 1. 增加 `_InternalDensityScale`

| 项目 | 内容 |
|------|------|
| **当前值** | 0.05 |
| **建议值** | 0.15 ~ 0.30 |
| **修改位置** | Unity Inspector → Material → Internal Density Scale |

#### 为什么要这么做？

```
原理推导：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Front-to-back 混合公式：
    C_out = C_in + (1 - α_in) × C_sample × α_sample
    α_out = α_in + (1 - α_in) × α_sample

问题：当 α_sample 被乘以 0.05 后：
    原始 α = 0.5  →  实际 α = 0.025 (2.5%)
    
    累积到 90% 不透明度需要：
    1 - (1 - 0.025)^n = 0.9
    解得 n ≈ 90 步
    
    但你的 Raymarching 只有 512 步，穿越整个体积
    实际每个像素可能只采样 100-200 步
    结果：永远累积不到足够的不透明度
```

#### 工程化难度：⭐ (最简单)

直接在 Unity Editor 中拖动滑块即可，无需修改代码。

---

### 2. 增加 `_BaseDensityAlpha`

| 项目 | 内容 |
|------|------|
| **当前值** | 0.1 |
| **建议值** | 0.3 ~ 0.5 |
| **修改位置** | Unity Inspector → Material → Base Alpha for Flat Areas |

#### 为什么要这么做？

```glsl
// 当前 shader 逻辑 (第 415-420 行)
float edgeFactor = smoothstep(_MinGradient, _MinGradient + 0.1, gradMag);
float opacityModulator = lerp(activeBaseAlpha, 1.0, 
                              min(edgeFactor * activeEdgeContrib, 1.0));
```

**解读这段代码**：

```
当 gradMag < _MinGradient (平坦区):
    edgeFactor ≈ 0
    opacityModulator = lerp(0.1, 1.0, 0) = 0.1
    
    → 平坦区只有 10% 的透明度贡献！
    
当 gradMag > _MinGradient + 0.1 (边缘区):
    edgeFactor ≈ 1
    opacityModulator = lerp(0.1, 1.0, 1) = 1.0
    
    → 边缘区有 100% 的透明度贡献
```

**海洋数据的问题**：大部分区域是"平坦"的（梯度小），全被压成 10%！

#### 工程化难度：⭐ (最简单)

同上，Inspector 调参即可。

---

### 3. 降低 `_MinGradient`

| 项目 | 内容 |
|------|------|
| **当前值** | 0.01 |
| **建议值** | 0.001 ~ 0.005 |
| **修改位置** | Unity Inspector → Material → Gradient visibility threshold |

#### 为什么要这么做？

```
梯度的物理含义：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

梯度 = ∂density/∂position ≈ (density[x+1] - density[x-1]) / 2

对于医学影像（CT）：
    骨骼边缘的梯度可能高达 0.3~0.5
    软组织边界也有 0.05~0.1
    → _MinGradient = 0.01 是合理的

对于海洋含氧量：
    数据是经过平滑/插值的连续场
    典型梯度可能只有 0.001~0.01
    → _MinGradient = 0.01 会把大部分数据判定为"无梯度"
```

#### 如何确定你的数据梯度范围？

你可以在 Python 中分析：

```python
import numpy as np

# 假设 data 是你的 3D 含氧量数据 (已归一化到 0-1)
grad_x = np.gradient(data, axis=0)
grad_y = np.gradient(data, axis=1)
grad_z = np.gradient(data, axis=2)
grad_mag = np.sqrt(grad_x**2 + grad_y**2 + grad_z**2)

print(f"梯度范围: {grad_mag.min():.6f} ~ {grad_mag.max():.6f}")
print(f"梯度中位数: {np.median(grad_mag):.6f}")
print(f"梯度 95 百分位: {np.percentile(grad_mag, 95):.6f}")
```

#### 工程化难度：⭐ (最简单)

Inspector 调参，但需要先分析数据来确定合理值。

---

### 4. 重新设计 Transfer Function

| 项目 | 内容 |
|------|------|
| **当前状态** | 使用 Viridis-like 通用色板 |
| **问题** | 缺乏氧气数据的语义表达 |
| **修改位置** | `default.tf` 或 TransferFunction Editor |

#### 为什么要这么做？

**当前色板（通用科学可视化）**：
```
密度 0.0   → 深紫色  ← 低值
密度 0.5   → 黄色    ← 中值
密度 1.0   → 深红色  ← 高值
```

**问题**：用户看到紫色，不知道这是"好"还是"坏"！

**建议的氧气专用色板**：
```
密度 0.0 ~ 0.2  → 深红色/黑色  ← 缺氧区（危险！）
密度 0.2 ~ 0.4  → 橙色/黄色    ← 低氧区（警告）
密度 0.4 ~ 0.6  → 绿色         ← 适氧区（正常）
密度 0.6 ~ 0.8  → 浅蓝色       ← 富氧区（良好）
密度 0.8 ~ 1.0  → 深蓝色/白色  ← 高氧区（极佳）
```

#### 实现方式

**方法 A：修改 default.tf 文件**

```json
{
  "version": 1,
  "colourPoints": [
    {"dataValue": 0.0,   "colourValue": {"r": 0.1, "g": 0.0, "b": 0.0, "a": 1.0}},
    {"dataValue": 0.2,   "colourValue": {"r": 0.8, "g": 0.2, "b": 0.1, "a": 1.0}},
    {"dataValue": 0.35,  "colourValue": {"r": 0.9, "g": 0.7, "b": 0.2, "a": 1.0}},
    {"dataValue": 0.5,   "colourValue": {"r": 0.2, "g": 0.8, "b": 0.3, "a": 1.0}},
    {"dataValue": 0.7,   "colourValue": {"r": 0.3, "g": 0.7, "b": 0.9, "a": 1.0}},
    {"dataValue": 1.0,   "colourValue": {"r": 0.1, "g": 0.3, "b": 0.9, "a": 1.0}}
  ],
  "alphaPoints": [
    {"dataValue": 0.0,  "alphaValue": 0.6},
    {"dataValue": 0.3,  "alphaValue": 0.3},
    {"dataValue": 0.5,  "alphaValue": 0.2},
    {"dataValue": 0.7,  "alphaValue": 0.3},
    {"dataValue": 1.0,  "alphaValue": 0.5}
  ]
}
```

**方法 B：运行时动态生成**

在 `RuntimeTransferFunctionEditor.cs` 中添加 "Ocean Oxygen" 预设按钮。

#### 工程化难度：⭐⭐ (简单)

只需编辑 JSON 文件或在 Editor 中手动调整控制点。

---

## 中期改进：改 Shader

### 1. 启用 Lighting（法向光照）

| 项目 | 内容 |
|------|------|
| **当前状态** | `LIGHTING_ON` 可能未启用 |
| **效果** | 给平坦区域添加立体感和深度线索 |
| **修改位置** | Shader 的 `#pragma multi_compile` 或 Material Keywords |

#### 为什么要这么做？

```
没有光照时：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    所有同密度的体素 → 同样的颜色
    结果：看起来像"雾"或"染色玻璃"，没有立体感

有光照时：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    同密度但法向不同 → 不同的明暗
    公式：color = diffuse × max(N·L, ambient) + specular
    结果：表面有高光和阴影，能感知形状
```

**当前 shader 的光照代码（第 290-300 行）**：
```glsl
float3 calculateLighting(float3 col, float3 normal, float3 lightDir, 
                         float3 eyeDir, float specularIntensity)
{
    normal *= (step(0.0, dot(normal, eyeDir)) * 2.0 - 1.0);
    float ndotl = max(lerp(0.0f, 1.5f, dot(normal, lightDir)), AMBIENT_LIGHTING_FACTOR);
    float3 diffuse = ndotl * col;
    float3 v = eyeDir;
    float3 r = normalize(reflect(-lightDir, normal));
    float rdotv = max(dot(r, v), 0.0);
    float3 specular = pow(rdotv, 32.0f) * float3(1.0f, 1.0f, 1.0f) * specularIntensity;
    return diffuse + specular;
}
```

**但只有在 `LIGHTING_ON` 启用时才会调用！**

#### 如何启用？

**方法 A：在 VolumeRenderedObject 中**
```csharp
// 查找 SetLightingEnabled 方法并调用
volumeRenderedObject.SetLightingEnabled(true);
```

**方法 B：直接设置 Material Keyword**
```csharp
material.EnableKeyword("LIGHTING_ON");
```

#### 工程化难度：⭐⭐ (简单)

只需调用现有 API 或设置关键字。

---

### 2. 启用 2D Transfer Function

| 项目 | 内容 |
|------|------|
| **当前状态** | 使用 1D TF（仅密度） |
| **改进** | 使用 2D TF（密度 × 梯度） |
| **修改位置** | 需要设置 `TF2D_ON` 关键字 |

#### 为什么要这么做？

```
1D Transfer Function:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
输入：density → 输出：RGBA

问题：
    - 密度 = 0.5 的"平坦高氧区" 
    - 密度 = 0.5 的"高氧与低氧交界处"
    ↓
    两者颜色完全相同！无法区分！


2D Transfer Function:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
输入：(density, gradient) → 输出：RGBA

解决：
    - (0.5, 低梯度) → 柔和的蓝色
    - (0.5, 高梯度) → 明亮的边界色
    ↓
    可以区分"内部"和"边界"！
```

**2D TF 可视化**：
```
     梯度 ↑
     高   │   ┌───────────┐
          │   │ 边界强调  │ ← 高对比、高不透明
          │   │  (亮色)   │
          │   └───────────┘
          │   ┌───────────┐
     低   │   │ 内部区域  │ ← 低对比、半透明
          │   │  (柔和色) │
          │   └───────────┘
          └───────────────────→ 密度
            低            高
```

#### 实现方式

1. 创建 2D Transfer Function 纹理
2. 设置 `TF2D_ON` 关键字
3. Shader 自动使用 `getTF2DColour(density, gradMagNorm)`

#### 工程化难度：⭐⭐⭐ (中等)

需要：
- 理解 `TransferFunction2D.cs` 的 Box 模型
- 设计合理的 2D 映射
- 可能需要创建新的 Editor UI

---

### 3. 增加 Raymarching 步数

| 项目 | 内容 |
|------|------|
| **当前值** | 512 步 |
| **建议值** | 1024 或 2048 步（内部观察时） |
| **修改位置** | Shader 第 340 行 `initRaymarch(ray, 512)` |

#### 为什么要这么做？

```
步长与细节的关系：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

体积对角线长度 = √3 ≈ 1.732
步长 = 1.732 / numSteps

512 步 → 步长 ≈ 0.0034 → 每个体素约 0.3% 的采样
1024步 → 步长 ≈ 0.0017 → 采样精度翻倍

当步长 > 数据变化频率时，会产生"欠采样"：
    - 快速变化的区域被跳过
    - 细节丢失
    - 边界模糊
```

**内部观察的特殊需求**：
- 外部观察：光线穿过整个体积，512 步够用
- 内部观察：光线起点在中间，每条射线更短，但需要更高精度来捕捉局部细节

#### 动态调整实现

```glsl
// 在 frag_VolumeSTCube 中
int maxSteps = isInside ? 1024 : 512;
RaymarchInfo raymarchInfo = initRaymarch(ray, maxSteps);
```

#### 工程化难度：⭐⭐ (简单)

修改一行代码。但要注意性能：步数翻倍 ≈ 帧率减半。

---

### 4. 添加局部对比度增强

| 项目 | 内容 |
|------|------|
| **目的** | 增强平坦区域内的微小变化 |
| **方法** | Histogram Equalization 或 Unsharp Masking |
| **修改位置** | 数据预处理或 Shader |

#### 为什么要这么做？

```
海洋数据的典型问题：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

原始数据范围：80-220 mg/L（归一化后 0.31-0.86）
视觉动态范围：只有 55%！

人眼对比灵敏度：约 2%
但如果数据只用了 55% 的色彩空间，
微小变化（比如 0.35 vs 0.37）就很难分辨。
```

**解决方案 A：数据预处理（Python）**

```python
# 对比度拉伸
data_min, data_max = np.percentile(data, [2, 98])
data_stretched = (data - data_min) / (data_max - data_min)
data_stretched = np.clip(data_stretched, 0, 1)
```

**解决方案 B：Shader 中实时处理**

```glsl
// 在 getDensity 后添加
float stretchedDensity = (density - _MinVal) / (_MaxVal - _MinVal);
stretchedDensity = saturate(stretchedDensity);
```

#### 工程化难度：⭐⭐⭐ (中等)

- 预处理方案：简单，但需要重新生成数据
- Shader 方案：需要暴露 `_ContrastMin` / `_ContrastMax` 参数

---

## 长期改进：架构重构

### 1. 多层渲染（Layered Volume Rendering）

| 项目 | 内容 |
|------|------|
| **概念** | 将数据分成多个语义层，分别渲染后合成 |
| **优势** | 每层可以有独立的颜色/透明度/混合模式 |

#### 为什么要这么做？

```
单层渲染的局限：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
所有数据用同一套规则渲染
→ 低氧区和高氧区用同样的透明度逻辑
→ 难以同时突出两者


多层渲染的优势：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 1: 缺氧区 (density < 0.3)
    → 红色，高不透明度，闪烁效果（警告）
    
Layer 2: 适氧区 (0.3 < density < 0.7)
    → 蓝绿色，低不透明度（背景）
    
Layer 3: 高氧边界 (高梯度区)
    → 白色边缘线（轮廓）

最终合成：Overlay 混合
```

#### 实现架构

```
                    ┌─────────────────┐
                    │  Volume Data    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐       ┌───────────┐
   │  Pass 1   │      │  Pass 2   │       │  Pass 3   │
   │ 缺氧层渲染 │      │ 适氧层渲染 │       │ 边界层渲染 │
   └─────┬─────┘      └─────┬─────┘       └─────┬─────┘
         │                  │                   │
         └───────────────────┼───────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  合成 Shader    │
                    │ (Additive/Blend)│
                    └─────────────────┘
```

#### 工程化难度：⭐⭐⭐⭐⭐ (困难)

需要：
- 多 Pass 渲染架构
- 每层独立的 RenderTexture
- 合成 Shader
- 新的 UI 来控制每层参数

---

### 2. 内部/外部双模式系统

| 项目 | 内容 |
|------|------|
| **概念** | 完全分离内部和外部观察的渲染逻辑 |
| **当前状态** | 用 `isInside` 布尔值切换参数 |
| **改进** | 使用独立的 Shader Variant 或 SubShader |

#### 为什么要这么做？

```
当前方案的问题：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if (isInside) {
    // 内部参数
} else {
    // 外部参数
}

问题：
1. 每个像素都要做条件判断 → 性能损失
2. 所有逻辑耦合在一个函数里 → 难维护
3. 无法为内部模式添加专属功能


改进后的架构：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SubShader "External Viewing" {
    // 标准 DVR
}

SubShader "Internal Viewing" {
    // X-Ray 风格
    // 增强的雾效果
    // 方向性环境光
}

C# 脚本根据相机位置自动切换 SubShader
```

#### 工程化难度：⭐⭐⭐⭐ (较困难)

需要：
- 重构 Shader 为多 SubShader
- 相机位置检测逻辑
- 平滑过渡（避免切换时跳变）

---

### 3. 阈值等值面着色（Threshold Isosurface）

| 项目 | 内容 |
|------|------|
| **概念** | 在特定密度值处生成"表面"，类似地形等高线 |
| **用途** | 清晰标记含氧量区间边界 |

#### 为什么要这么做？

```
体渲染的模糊性：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
所有密度值都被连续渲染
→ 用户难以判断"当前位置的含氧量是多少"


等值面的清晰性：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在 density = 0.3, 0.5, 0.7 处绘制半透明"皮肤"
用户可以明确看到：
    "我现在在 0.5 这层之上，0.7 那层之下"
    → 含氧量大约在 0.5-0.7 之间
```

**视觉效果**：

```
        ─────────────────────────
        ░░░░░░░░░░░░░░░░░░░░░░░░░ ← 0.7 等值面（蓝色半透明）
        ░░░░░░░░░░░░░░░░░░░░░░░░░
        ─────────────────────────
                  ▲
               观察者
        ─────────────────────────  
        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ← 0.5 等值面（绿色半透明）
        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
        ─────────────────────────
        █████████████████████████ ← 0.3 等值面（红色半透明）
        ─────────────────────────
```

#### 实现方式

```glsl
// 在 raymarching 循环中添加
float isoValue1 = 0.3;
float isoValue2 = 0.5;
float isoValue3 = 0.7;

// 检测过零点（从一侧穿越到另一侧）
if (prevDensity < isoValue1 && density >= isoValue1) {
    // 绘制红色等值面
    col += float4(1, 0.2, 0.1, 0.3) * (1 - col.a);
}
// ... 类似处理其他等值面
```

#### 工程化难度：⭐⭐⭐ (中等)

需要：
- 修改 Raymarching 循环
- 暴露等值面阈值参数
- 可选：等值面颜色自定义 UI

---

## 工程化实现优先级

### 推荐实施顺序

```
第一阶段：快速见效（1-2 小时）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────────────┐
│ 1. 调整 _InternalDensityScale: 0.05 → 0.2          │ ⭐
│ 2. 调整 _BaseDensityAlpha: 0.1 → 0.4               │ ⭐
│ 3. 降低 _MinGradient: 0.01 → 0.003                 │ ⭐
│ 4. 启用 Lighting                                    │ ⭐⭐
└─────────────────────────────────────────────────────┘

预期效果：整体可见性大幅提升，不再是"雾"


第二阶段：语义增强（2-4 小时）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────────────┐
│ 5. 设计氧气专用 Transfer Function                   │ ⭐⭐
│ 6. 调整 Alpha 曲线（缺氧区高可见）                  │ ⭐⭐
│ 7. 增加 Raymarching 步数（内部时）                  │ ⭐⭐
└─────────────────────────────────────────────────────┘

预期效果：颜色有语义，缺氧区明显


第三阶段：进阶优化（4-8 小时）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────────────┐
│ 8. 启用 2D Transfer Function                        │ ⭐⭐⭐
│ 9. 添加阈值等值面                                   │ ⭐⭐⭐
│ 10. 对比度增强预处理                                │ ⭐⭐⭐
└─────────────────────────────────────────────────────┘

预期效果：边界清晰，定量信息可读


第四阶段：架构升级（1-2 周）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────────────┐
│ 11. 多层渲染                                        │ ⭐⭐⭐⭐⭐
│ 12. 内/外双模式 SubShader                           │ ⭐⭐⭐⭐
└─────────────────────────────────────────────────────┘

预期效果：专业级可视化，完全定制化
```

---

### 投入产出分析

| 改进项 | 工时 | 效果提升 | ROI |
|--------|------|----------|-----|
| 调参数（1-4） | 0.5h | ★★★★☆ | 极高 |
| 专用 TF（5-6） | 2h | ★★★★☆ | 高 |
| 启用 2D TF（8） | 4h | ★★★☆☆ | 中 |
| 阈值等值面（9） | 4h | ★★★☆☆ | 中 |
| 多层渲染（11） | 20h | ★★★★★ | 低（长期高） |

---

## 附录：快速测试脚本

创建一个测试脚本来快速尝试不同参数组合：

```csharp
// OxygenVisualizationTester.cs
using UnityEngine;

public class OxygenVisualizationTester : MonoBehaviour
{
    public Material volumeMaterial;
    
    [Header("Preset Configurations")]
    public bool usePresetA_HighVisibility;
    public bool usePresetB_EdgeEmphasis;
    public bool usePresetC_Balanced;
    
    void Update()
    {
        if (usePresetA_HighVisibility)
        {
            ApplyPresetA();
            usePresetA_HighVisibility = false;
        }
        // ... 类似处理其他预设
    }
    
    void ApplyPresetA()
    {
        volumeMaterial.SetFloat("_InternalDensityScale", 0.3f);
        volumeMaterial.SetFloat("_BaseDensityAlpha", 0.5f);
        volumeMaterial.SetFloat("_MinGradient", 0.002f);
        volumeMaterial.SetFloat("_EdgeContribution", 0.5f);
        Debug.Log("Applied Preset A: High Visibility");
    }
}
```

---

**下一步行动建议**：从第一阶段开始，用 30 分钟调整 Inspector 中的参数，观察效果变化。如果效果明显改善但仍不满意，再进入第二阶段。
