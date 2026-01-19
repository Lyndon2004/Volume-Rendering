# 氧气专用 Transfer Function 快速部署指南

## 文件清单

生成了以下文件，用于海洋含氧量的科学可视化：

1. **`oxygen_semantic.tf`** - JSON 格式的转移函数定义
   - 位置：`/RenderingModule/oxygen_semantic.tf`
   - 用途：定义缺氧→适氧→高氧的颜色与透明度映射

2. **`OxygenTransferFunctionManager.cs`** - C# 管理脚本
   - 位置：`/RenderingModule/Assets/Scripts/VolumeObject/OxygenTransferFunctionManager.cs`
   - 用途：运行时加载与切换不同的 TF 预设

---

## 部署步骤

### 步骤 1：移动 TF 文件到 Resources 目录

```bash
# 在项目根目录执行
mkdir -p RenderingModule/Assets/Resources
mv RenderingModule/oxygen_semantic.tf RenderingModule/Assets/Resources/oxygen_semantic.tf
```

**或在 Unity Editor 中**：
- 在 `Assets/Resources` 文件夹下新建文件夹（如果不存在）
- 将 `oxygen_semantic.tf` 拖入 `Resources` 文件夹
- Unity 会自动识别

### 步骤 2：将脚本添加到场景

- 在你的体渲染 GameObject 上添加 `OxygenTransferFunctionManager` 脚本
- 在 Inspector 中，将 VolumeRenderedObject 的引用拖到 `Volume Object` 字段
- 确保 Semantic TF Path 默认值 `oxygen_semantic` 无需改动

### 步骤 3：加载 Transfer Function

**方式 A：自动加载（推荐）**
- 脚本的 `Start()` 方法会自动加载语义 TF
- 运行场景即可看到氧气语义的可视化

**方式 B：手动加载（编辑器测试）**
```csharp
// 在任何脚本中调用
OxygenTransferFunctionManager manager = GetComponent<OxygenTransferFunctionManager>();
manager.LoadSemanticTransferFunction();
```

---

## 快捷键与实时对比

运行场景后，使用以下快捷键：

| 按键 | 功能 |
|------|------|
| **T** | 循环切换可视化模式（Default → Semantic → HighContrast） |
| **L** | 打印当前 TF 信息与语义说明到控制台 |

**三种模式说明**：

1. **Default**（默认通用色板）
   - 原始的 VolumeSTCube 色板
   - 用途：对标对比

2. **SemanticOxygen**（氧气语义，推荐）
   - 缺氧区（红）→ 适氧区（绿蓝）→ 高氧区（深蓝）
   - 透明度：缺氧高可见 → 适氧低可见（背景） → 高氧中等可见
   - 用途：科学分析与展示

3. **HighContrast**（高对比，诊断用）
   - 极端化的彩虹色与 α 曲线
   - 用途：快速测试与数据分布诊断

---

## 语义设计详解

### 颜色映射（密度 → 颜色）

```
0.0  ───→  深红/黑（缺氧危险区）
0.15 ───→  鲜红色（低氧警告）
0.35 ───→  橙色（低氧过渡）
0.5  ───→  绿色（适氧基准）← 用户关注的"正常"区域
0.65 ───→  浅蓝（高氧良好）
0.85 ───→  深蓝（高氧优异）
1.0  ───→  极深蓝（最高含氧）
```

### 透明度映射（密度 → Alpha）

```
密度      Alpha    意义
0.0       0.0      无数据（完全透明）
0.08      0.85     缺氧区→立即可见
0.2       0.95     低氧区→强调可见
0.35      0.65     过渡区→中等可见
0.5       0.40     适氧区→淡化背景（低优先级）
0.65      0.50     高氧区→部分突出
0.85      0.60     高氧区→可见
1.0       0.70     极高氧→稳定显示
```

### 设计原则

1. **含氧量语义化**
   - 红色 = 危险（缺氧）
   - 绿色 = 正常（适氧）
   - 蓝色 = 良好（高氧）
   - 不使用梯度驱动的边界强调（Edge=0）

2. **优先级突出**
   - 缺氧区（最关键）：最高透明度与鲜艳色
   - 适氧区（背景）：最低透明度（不抢戏）
   - 高氧区（次要）：中等透明度（点缀）

3. **面向小数据优化**
   - 颜色曲线平滑过渡（无突跳）
   - 透明度曲线考虑小数据的采样步长（512-2048）
   - 与小数据参数组合：Base=1, Internal=0.6-1.0, Edge=0

---

## 推荐的使用参数组合

结合氧气语义 TF 使用以下材质参数：

```
BaseDensityAlpha:       1.0（保留所有平坦区）
InternalDensityScale:   0.8 ~ 1.0（小数据可激进）
EdgeContribution:       0（不用梯度描边）
MinGradient:            0.001 ~ 0.01（默认，不影响 Edge=0）
RaymarchSteps:          1024 ~ 2048（小数据内部观察时）
```

**启用照明（可选但推荐）**：
- `LIGHTING_ON` keyword 启用
- `_VolumeLightFactor`: 0.3 ~ 0.7
- 为平坦区增加立体感，不改变语义

---

## 故障排查

### 问题 1：无法加载 TF 文件

**症状**：控制台警告 "未找到 Transfer Function 文件"

**解决**：
1. 确认文件路径：`Assets/Resources/oxygen_semantic.tf`
2. 检查文件名（区分大小写）
3. 在 Unity Editor 中手动导入文件

### 问题 2：切换快捷键无反应

**症状**：按 T 键无法切换模式

**解决**：
1. 确认 VolumeRenderedObject 引用正确
2. 检查是否在编辑器或播放模式运行
3. 打开控制台查看错误日志

### 问题 3：颜色不如预期

**症状**：看到的颜色与文档描述不符

**解决**：
1. 在 Shader 中检查是否启用了色彩空间转换（Linear vs Gamma）
2. 用 HighContrast 模式诊断数据分布
3. 按 L 键查看控制台的语义说明

---

## 进阶：自定义 Transfer Function

如果需要微调氧气 TF，可以：

### 方式 A：直接编辑 JSON 文件

```json
{
  "colourPoints": [
    {"dataValue": 0.0, "colourValue": {"r": 0.1, "g": 0.0, "b": 0.0, "a": 1.0}},
    // ... 修改 r, g, b 值（0.0-1.0）
  ],
  "alphaPoints": [
    {"dataValue": 0.0, "alphaValue": 0.0},
    // ... 修改 alphaValue（0.0-1.0）
  ]
}
```

修改后保存，Unity 会自动重新加载。

### 方式 B：在 Editor 中可视化调整

1. 在 `OxygenTransferFunctionManager.cs` 中添加一个 `CreateCustomPreset()` 方法
2. 在 Inspector 中公开颜色与 α 的控制点参数
3. 实时调整并导出为新的 `.tf` 文件

### 方式 C：使用 RuntimeTransferFunctionEditor

如果项目中有 `RuntimeTransferFunctionEditor.cs`，可以在运行时直接编辑 TF UI。

---

## 验证清单

- [ ] 文件 `oxygen_semantic.tf` 存在于 `Assets/Resources/` 目录
- [ ] 脚本 `OxygenTransferFunctionManager.cs` 已添加到体渲染 GameObject
- [ ] Inspector 中 Volume Object 字段正确关联
- [ ] 运行场景后，看到的颜色是红→橙→绿→蓝的渐变（非通用彩虹色）
- [ ] 按 T 键可以切换三种模式
- [ ] 按 L 键可以在控制台查看语义说明
- [ ] 材质参数设置为：Base=1, Internal=0.6-1.0, Edge=0

---

## 下一步（可选）

1. **启用 2D Transfer Function**（高级）
   - 在 X 轴保留含氧量语义
   - 在 Y 轴用低梯度区分"均质区"vs"过渡带"
   - 需要修改 Shader 启用 `TF2D_ON` keyword

2. **对比度拉伸预处理**
   - 如果实际数据范围 < 0-255 全域，用 Python 拉伸
   - 提升色彩与透明度的动态范围

3. **多层渲染**（长期）
   - 分别渲染缺氧/适氧/高氧三层
   - 每层独立参数与混合模式
   - 实现更精细的语义表达

---

**现在就可以开始使用！按照步骤 1-3 部署，然后在场景中用 T 键对比效果。**
