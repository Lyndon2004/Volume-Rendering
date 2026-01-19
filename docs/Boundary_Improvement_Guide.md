# 海洋数据边界处理改进指南

## 问题诊断

你的 `2_Smooth.py` 中的 `clipedChinaFrame` 函数存在以下问题：

```python
# 原始代码：
temp_res[np.tile(df_grid_geo['val'].to_numpy(), (zLength)).tolist()] = 0.0
```

**问题分析**：
1. 陆地直接被设为 0（最低值）
2. 边界处形成一圈最低值的"项链"
3. 后续在 `map_values_with_condition` 中被映射为 1（暗淡）
4. 在渲染时显示为缺氧红色（因为极低值被映射到红区）
5. 相机穿入时颜色突变（内外参数不同导致）

---

## 改进方案

### 方案 A：Neumann 边界条件（推荐 ⭐⭐⭐）

```python
boundary_method='neumann'
clipping_value=1
```

**原理**：
- 边界处的梯度为 0，所以边界值 = 相邻内部的有效值
- 陆地区域用内部海洋数据的值来"延伸"
- 避免人工的低值边界

**优势**：
- ✅ 边界值不再是极低的 0
- ✅ 视觉上边界红圈消失
- ✅ 内外观察颜色一致
- ✅ 数据连续性最好

**劣势**：
- ✗ 陆地边界会显示一些"幽灵"的海洋颜色

**何时使用**：
- 追求视觉清晰度
- 不关心陆地的确切表示
- 内部沉浸式观察（你的使用场景）

---

### 方案 B：高斯模糊平滑（推荐 ⭐⭐⭐）

```python
boundary_method='gaussian'
clipping_value=0  # 保留原始裁切
```

**原理**：
- 对整个体积应用高斯模糊
- 在边界附近创建淡出掩膜
- 边界逐渐过渡到裁切值

**优势**：
- ✅ 平滑自然的过渡
- ✅ 不会产生"幽灵"效果
- ✅ 视觉最柔和

**劣势**：
- ✗ 可能稍微模糊内部数据细节
- ✗ 边界仍有轻微的灰色

**何时使用**：
- 追求视觉平滑
- 内部细节精度要求不是最高
- 想保持陆地与海洋的区分

---

### 方案 C：反射填充（保守方案 ⭐⭐）

```python
boundary_method='reflect'
clipping_value=0
```

**原理**：
- 用镜像的内部数据填充边界
- 保持数据的对称性

**优势**：
- ✅ 边界数据完整
- ✅ 保持周期性结构

**劣势**：
- ✗ 海洋边界会产生人工的对称结构
- ✗ 可能不符合物理意义

**何时使用**：
- 需要最少数据丢失
- 数据具有某种周期性

---

### 方案 D：无边界处理（原始）

```python
boundary_method='none'
clipping_value=0
```

**就是原始的 `2_Smooth.py`**，会产生你当前看到的问题。

---

## 快速切换方式

在 `2_Smooth_improved.py` 中，只需修改以下两行：

```python
# 第 ~150 行
temp_res = clipedChinaFrame_improved(
    data,
    china_mask,
    zLength, xLength, yLength,
    boundary_method='neumann',      # ← 改这里：'neumann' / 'gaussian' / 'none'
    clipping_value=1                # ← 改这里：1（Neumann） / 0（其他）
)
```

---

## 对比表

| 特性 | Neumann | Gaussian | Reflect | None |
|------|---------|----------|---------|------|
| 边界红圈 | ✅ 消失 | ✅ 消失 | ⚠️ 减弱 | ❌ 明显 |
| 视觉平滑度 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| 数据完整性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 颜色一致性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| 陆地表示 | 有幽灵 | 清晰 | 清晰 | 清晰 |
| 推荐度 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ❌ |

---

## 使用步骤

### 步骤 1：用改进脚本重新生成数据

```bash
cd /Users/yiquan/Desktop/VolumeSTCube/DataTransformationModule
python 2_Smooth_improved.py
```

**输出**：
- 新文件：`UnityRawData/*_improved_boundary.raw`
- 新配置：`UnityRawData/*_improved_boundary.raw.ini`

### 步骤 2：在 Unity 中加载新数据

1. 注册新的 `.raw` 和 `.ini` 文件
2. 在 VolumeRenderedObject 中加载新数据
3. 使用相同的 `oxygen_semantic.tf` TF 文件

### 步骤 3：对比效果

- 打开原始数据和改进后的数据，并排观察
- 检查外部边界是否不再有红圈
- 检查内部观察时颜色是否稳定

---

## 高级：微调参数

```python
def neumann_boundary(data_3d, boundary_width=2):
    # boundary_width 控制有多少层被替代
    # 2 = 边界 2 层用相邻值（通常足够）
    # 3-5 = 更宽的过渡带（更平滑但失效更多数据）
    pass

def gaussian_smooth_boundary(data_3d, sigma=1.5, boundary_fade_width=5):
    # sigma: 高斯模糊强度（1.0-3.0，越大越模糊）
    # boundary_fade_width: 淡出宽度（3-10 像素）
    pass
```

---

## 如果你只是想快速修复当前数据

不用重新生成，直接在渲染端修改：

1. **在 Inspector 中设置 Min val = 0.1**（忽略极低值）
2. **修改 oxygen_semantic.tf 的缺氧区 Alpha**

```json
"alphaPoints": [
  {"dataValue": 0.0, "alphaValue": 0.0},     // 极低：完全透明
  {"dataValue": 0.05, "alphaValue": 0.1},    // 超低：极淡
  {"dataValue": 0.1, "alphaValue": 0.5},     // 低值：中度
  ...
]
```

这样边界红圈会显著减弱。

但**根本方案**还是重新生成数据（用 Neumann 边界）。

---

## 总结

- **立即用**：修改 oxygen_semantic.tf 的 Alpha 曲线
- **快速修复**：用 `boundary_method='neumann'` 重新生成（推荐）
- **最平滑**：用 `boundary_method='gaussian'` 重新生成
- **长期方案**：集成到你的数据管道中，每次生成都用改进版本

需要我帮你运行改进脚本生成新数据吗？或者给一个完整的"一键修复" Python 脚本，直接处理已生成的数据文件？
