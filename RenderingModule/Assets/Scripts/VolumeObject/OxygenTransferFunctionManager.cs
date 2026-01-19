using UnityEngine;
using System.Collections.Generic;

namespace UnityVolumeRendering
{
    /// <summary>
    /// 海洋含氧量可视化的 Transfer Function 管理器
    /// 提供快速切换和实时对比的功能
    /// </summary>
    public class OxygenTransferFunctionManager : MonoBehaviour
    {
        [SerializeField]
        private VolumeRenderedObject volumeObject;

        [Header("Transfer Function Files")]
        [SerializeField]
        private string semanticTFPath = "oxygen_semantic";  // Resources 相对路径

        public enum OxygenVisualizationMode
        {
            Default,           // 默认（通用色板）
            SemanticOxygen,    // 氧气语义（推荐）
            HighContrast       // 高对比度（测试用）
        }

        private OxygenVisualizationMode currentMode = OxygenVisualizationMode.SemanticOxygen;

        void Start()
        {
            if (volumeObject == null)
                volumeObject = GetComponent<VolumeRenderedObject>();

            // 默认加载语义 TF
            LoadSemanticTransferFunction();
        }

        void Update()
        {
            // 快捷键切换（仅在编辑器或开发模式下）
            if (Input.GetKeyDown(KeyCode.T))
            {
                CycleVisualizationMode();
            }

            if (Input.GetKeyDown(KeyCode.L))
            {
                LogCurrentTFInfo();
            }
        }

        /// <summary>
        /// 加载氧气语义 Transfer Function（从 Resources 加载）
        /// 设计原则：
        /// - 缺氧区（0.0-0.2）：红色 + 高 α → 立即可见的警告
        /// - 低氧区（0.2-0.35）：橙色 + 高 α → 明显警告
        /// - 过渡区（0.35-0.5）：绿黄色 → 密度变化带
        /// - 适氧区（0.5-0.65）：绿蓝色 + 低 α → 背景/基准
        /// - 高氧区（0.65-0.85）：蓝色 + 中 α → 展示良好含氧
        /// - 极高氧区（0.85-1.0）：深蓝色 + 中高 α → 最优状态
        /// </summary>
        public void LoadSemanticTransferFunction()
        {
            if (volumeObject == null) return;

            TransferFunction tf = Resources.Load<TransferFunction>(semanticTFPath);
            if (tf != null)
            {
                volumeObject.SetTransferFunction(tf);
                currentMode = OxygenVisualizationMode.SemanticOxygen;
                Debug.Log("✓ 已加载氧气语义 Transfer Function");
            }
            else
            {
                Debug.LogWarning($"未找到 Transfer Function 文件: {semanticTFPath}");
                Debug.LogWarning("请确保文件位于 Assets/Resources/ 目录下，文件名为 oxygen_semantic.tf");
            }
        }

        /// <summary>
        /// 加载默认 Transfer Function（恢复原始通用色板）
        /// 用于对比测试
        /// </summary>
        public void LoadDefaultTransferFunction()
        {
            if (volumeObject == null) return;

            TransferFunction tf = TransferFunctionDatabase.CreateTransferFunction();
            volumeObject.SetTransferFunction(tf);
            currentMode = OxygenVisualizationMode.Default;
            Debug.Log("✓ 已恢复默认 Transfer Function");
        }

        /// <summary>
        /// 高对比度模式（用于测试与诊断）
        /// 将颜色范围极端化，便于观察数据分布
        /// </summary>
        public void LoadHighContrastTransferFunction()
        {
            if (volumeObject == null) return;

            TransferFunction tf = ScriptableObject.CreateInstance<TransferFunction>();

            // 极端颜色与透明度曲线，用于视觉测试
            tf.AddControlPoint(new TFColourControlPoint(0.0f, new Color(0.0f, 0.0f, 0.0f, 1.0f)));      // 黑
            tf.AddControlPoint(new TFColourControlPoint(0.25f, new Color(1.0f, 0.0f, 0.0f, 1.0f)));     // 红
            tf.AddControlPoint(new TFColourControlPoint(0.5f, new Color(0.0f, 1.0f, 0.0f, 1.0f)));      // 绿
            tf.AddControlPoint(new TFColourControlPoint(0.75f, new Color(0.0f, 0.0f, 1.0f, 1.0f)));     // 蓝
            tf.AddControlPoint(new TFColourControlPoint(1.0f, new Color(1.0f, 1.0f, 1.0f, 1.0f)));      // 白

            tf.AddControlPoint(new TFAlphaControlPoint(0.0f, 0.0f));
            tf.AddControlPoint(new TFAlphaControlPoint(0.15f, 0.9f));
            tf.AddControlPoint(new TFAlphaControlPoint(0.5f, 0.5f));
            tf.AddControlPoint(new TFAlphaControlPoint(1.0f, 0.9f));

            tf.GenerateTexture();
            volumeObject.SetTransferFunction(tf);
            currentMode = OxygenVisualizationMode.HighContrast;
            Debug.Log("✓ 已加载高对比度 Transfer Function（诊断用）");
        }

        /// <summary>
        /// 循环切换可视化模式（按下 T 键触发）
        /// </summary>
        public void CycleVisualizationMode()
        {
            int nextMode = ((int)currentMode + 1) % 3;
            currentMode = (OxygenVisualizationMode)nextMode;

            switch (currentMode)
            {
                case OxygenVisualizationMode.Default:
                    LoadDefaultTransferFunction();
                    break;
                case OxygenVisualizationMode.SemanticOxygen:
                    LoadSemanticTransferFunction();
                    break;
                case OxygenVisualizationMode.HighContrast:
                    LoadHighContrastTransferFunction();
                    break;
            }

            Debug.Log($"切换到模式: {currentMode}");
        }

        /// <summary>
        /// 输出当前 Transfer Function 的信息到控制台（便于调试）
        /// </summary>
        private void LogCurrentTFInfo()
        {
            Debug.Log($"当前可视化模式: {currentMode}");
            Debug.Log("快捷键提示:");
            Debug.Log("  T - 循环切换可视化模式");
            Debug.Log("  L - 打印当前 TF 信息");
            Debug.Log("语义设计:");
            Debug.Log("  缺氧区（0.0-0.2）：红色 + 高透明度（警告）");
            Debug.Log("  低氧区（0.2-0.35）：橙色（关注）");
            Debug.Log("  过渡区（0.35-0.5）：绿黄色（过渡）");
            Debug.Log("  适氧区（0.5-0.65）：绿蓝色 + 低透明度（背景）");
            Debug.Log("  高氧区（0.65-0.85）：蓝色（良好）");
            Debug.Log("  极高氧区（0.85-1.0）：深蓝色（优异）");
        }

        /// <summary>
        /// 获取当前模式
        /// </summary>
        public OxygenVisualizationMode GetCurrentMode()
        {
            return currentMode;
        }
    }
}
