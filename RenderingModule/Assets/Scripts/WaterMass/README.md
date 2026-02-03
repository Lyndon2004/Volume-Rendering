# WaterMass Unity 模块

本文件夹包含**水团追踪系统**的可视化组件。这些脚本负责将 Python 后端（`DataTransformationModule`）生成的数据在 Unity 渲染引擎中展示出来。

## 组件概览

### 1. `WaterMassManager.cs`（总控制器）
**职责：** 整个可视化系统的"大脑"。
*   **数据导入：** 读取 Python 生成的 `trajectory.json` 文件。
*   **同步协调：** 统一调度 `MeshPlayer` 和 `TrajectoryRenderer`。当时间变化时，它会同时通知模型更新和轨迹线重绘。
*   **公开接口：**
    *   `OnTimeSliderChanged(float normalizedTime)`：将此方法绑定到 UI Slider（值范围 0.0 到 1.0），即可实现时间轴拖拽。
    *   `SetTime(int timeIndex)`：跳转到指定帧。

### 2. `MeshSequencePlayer.cs`（模型播放器）
**职责：** 处理 3D 形状动画。
*   **功能：** 按需从硬盘加载 `.obj` 文件。
*   **缓存机制：** 已加载的帧会被缓存，再次访问时无需重新读取，实现快速回放。
*   **依赖组件：** 需要在同一 GameObject 上挂载 `MeshFilter` 和 `MeshRenderer`。

### 3. `TrajectoryRenderer.cs`（轨迹渲染器）
**职责：** 可视化水团的运动历史。
*   **功能：** 绘制一条连接各时间点水团质心的线条。
*   **动态生长：** 随着时间推进，线条会"生长"出来，只显示*到当前时刻为止*的路径。
*   **颜色编码：** 使用渐变色（蓝色 -> 红色）来表示时间流逝。
*   **依赖组件：** 需要 `LineRenderer` 组件。

### 4. `SimpleObjLoader.cs`（OBJ 加载工具）
**职责：** 一个轻量级的运行时 OBJ 解析器。
*   **为什么需要它？** Unity 默认不支持在运行时加载 `.obj` 文件（仅限编辑器模式）。此脚本将文本格式的 OBJ 文件解析为 Unity `Mesh` 对象。

### 5. `WaterMassDataContainer.cs`（数据容器）
**职责：** 定义与 JSON 文件对应的数据结构。
*   **功能：** 用于 `JsonUtility` 反序列化 `trajectory.json` 中的质心坐标和体积数据。

## Unity 编辑器配置步骤

1.  **创建管理器：**
    *   在场景中创建空物体，命名为 `WaterMassSystem`。
    *   添加 `WaterMassManager` 脚本。
2.  **创建模型物体：**
    *   创建子物体，命名为 `WaterMassMesh`。
    *   添加 `MeshFilter` 和 `MeshRenderer` 组件。
    *   添加 `MeshSequencePlayer` 脚本。
    *   为 `MeshRenderer` 指定一个材质（例如：半透明蓝色材质）。
3.  **创建轨迹物体：**
    *   创建子物体，命名为 `TrajectoryPath`。
    *   添加 `LineRenderer` 组件。
    *   添加 `TrajectoryRenderer` 脚本。
    *   设置 `LineRenderer` 的材质（例如：发光粒子材质效果更佳）。
4.  **连接引用：**
    *   选中 `WaterMassSystem`。
    *   将 `WaterMassMesh` 拖拽到 **Mesh Player** 插槽。
    *   将 `TrajectoryPath` 拖拽到 **Trajectory Renderer** 插槽。
5.  **配置数据路径：**
    *   在 `WaterMassManager` 的 Inspector 面板中，将 **Data Folder** 设置为 Python 脚本输出文件的绝对路径（例如：`/Users/.../DataTransformationModule/MultiVarOutput`）。

## 数据流向
```
Python 后端 -> (生成 .obj 和 .json) -> 磁盘 -> WaterMassManager -> Unity 场景
```
