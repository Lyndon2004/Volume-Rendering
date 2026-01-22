# 数据转换与多变量水团处理工具使用说明

本目录下的脚本用于将原始的海洋体素数据（.raw/.ini）处理为可视化的 3D 网格模型（.obj）和轨迹数据（.json）。

## 核心脚本

### 1. `multi_var_processor.py` (推荐)
这是最新的**多变量融合处理工具**。它允许你同时读取多个变量（如叶绿素、硝酸盐、盐度），并通过自定义逻辑公式来定义“水团”。

#### **接口说明**

```python
processor = WaterMassProcessor(data_root_path)

# 1. 注册变量
# var_name: 变量在公式中的名字 (如 'temp')
# pattern: 文件路径匹配模式 (支持通配符 *)
processor.register_variable("chloro", "chlorophyll/*chlorophyll*.raw.ini")
processor.register_variable("no3",    "NO3/*NO3*.raw.ini")

# 2. 执行处理
# logic: Numpy 风格的布尔表达式
# mesh_name_prefix: 输出文件的前缀
processor.process_sequence(
    output_dir="Output", 
    criteria_expression="(chloro > 50) & (no3 < 100)", 
    mesh_name_prefix="MyWaterMass"
)
```

#### **如何运行**

```bash
# 默认会读取 ../Data 目录下的数据
python multi_var_processor.py

# 或者指定数据目录
python multi_var_processor.py "D:/MyOceanData"
```

---

### 2. `extract_isosurface.py` (单变量)
基础版工具，仅支持单一变量的阈值提取。适合简单的测试。

```bash
# 修改脚本中的 INPUT_DIR 和 THRESHOLD 变量后运行
python extract_isosurface.py
```

### 3. `calculate_trajectory.py`
计算水团重心的辅助工具。`multi_var_processor.py` 内部已经集成了这个功能，但你可以单独运行它来分析特定变量。

---

## 输入数据要求
*   **格式**：必须包含 `.raw` 数据文件和对应的 `.raw.ini` 描述文件。
*   **结构**：建议按变量分文件夹存放，例如：
    ```
    Data/
      ├── chlorophyll/
      ├── NO3/
      └── salt/
    ```

## 输出结果
运行脚本后，将在输出目录生成：
1.  **3D 模型序列**：`WaterMass_t0.obj`, `WaterMass_t1.obj` ...
    *   可直接拖入 Unity 使用。
2.  **轨迹文件**：`WaterMass_trajectory.json`
    *   包含每一帧的重心坐标 `[x, y, z]` 和体积大小。

## 依赖库
请确保安装以下库：
```bash
pip install numpy scikit-image trimesh
```
