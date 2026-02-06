using UnityEngine;

namespace UnityVolumeRendering
{
    /// <summary>
    /// 水团时间序列的时间轴 UI 组件
    /// 提供滑动条、播放控制按钮等界面
    /// </summary>
    public class WaterMassTimelineUI : MonoBehaviour
    {
        [Header("References")]
        public WaterMassVolumeController controller;
        
        [Header("UI Settings")]
        public bool showUI = true;
        public KeyCode toggleUIKey = KeyCode.H;
        
        [Header("Position")]
        public float bottomMargin = 50f;
        public float panelWidth = 600f;
        public float panelHeight = 80f;
        
        // 样式
        private GUIStyle sliderStyle;
        private GUIStyle buttonStyle;
        private GUIStyle labelStyle;
        private GUIStyle boxStyle;
        private bool stylesInitialized = false;
        
        void Start()
        {
            if (controller == null)
            {
                controller = GetComponent<WaterMassVolumeController>();
            }
        }
        
        void Update()
        {
            // 切换 UI 显示
            if (Input.GetKeyDown(toggleUIKey))
            {
                showUI = !showUI;
            }
        }
        
        void OnGUI()
        {
            if (!showUI || controller == null) return;
            
            InitStyles();
            DrawTimeline();
        }
        
        void InitStyles()
        {
            if (stylesInitialized) return;
            
            sliderStyle = new GUIStyle(GUI.skin.horizontalSlider);
            
            buttonStyle = new GUIStyle(GUI.skin.button);
            buttonStyle.fontSize = 16;
            buttonStyle.fixedHeight = 30;
            
            labelStyle = new GUIStyle(GUI.skin.label);
            labelStyle.fontSize = 12;
            labelStyle.alignment = TextAnchor.MiddleCenter;
            labelStyle.normal.textColor = Color.white;
            
            boxStyle = new GUIStyle(GUI.skin.box);
            boxStyle.normal.background = MakeTexture(2, 2, new Color(0.1f, 0.1f, 0.15f, 0.9f));
            
            stylesInitialized = true;
        }
        
        void DrawTimeline()
        {
            float panelX = (Screen.width - panelWidth) / 2;
            float panelY = Screen.height - bottomMargin - panelHeight;
            
            Rect panelRect = new Rect(panelX, panelY, panelWidth, panelHeight);
            
            GUILayout.BeginArea(panelRect, boxStyle);
            GUILayout.Space(5);
            
            // 标题行
            GUILayout.BeginHorizontal();
            GUILayout.FlexibleSpace();
            GUILayout.Label($"🌊 Water Mass Timeline - Frame {controller.CurrentFrame + 1}/{controller.TotalFrames}", 
                new GUIStyle(labelStyle) { fontSize = 14, fontStyle = FontStyle.Bold });
            GUILayout.FlexibleSpace();
            GUILayout.EndHorizontal();
            
            GUILayout.Space(5);
            
            // 时间轴滑动条
            GUILayout.BeginHorizontal();
            GUILayout.Space(10);
            
            int newFrame = Mathf.RoundToInt(GUILayout.HorizontalSlider(
                controller.CurrentFrame, 
                0, 
                controller.TotalFrames - 1,
                GUILayout.ExpandWidth(true)
            ));
            
            if (newFrame != controller.CurrentFrame && !controller.IsLoading)
            {
                controller.GoToFrame(newFrame);
            }
            
            GUILayout.Space(10);
            GUILayout.EndHorizontal();
            
            GUILayout.Space(5);
            
            // 控制按钮行
            GUILayout.BeginHorizontal();
            GUILayout.FlexibleSpace();
            
            // 速度调节
            GUILayout.Label($"Speed: {1f / controller.secondsPerFrame:F1}x", labelStyle, GUILayout.Width(80));
            
            if (GUILayout.Button("−", buttonStyle, GUILayout.Width(30)))
            {
                controller.secondsPerFrame = Mathf.Min(5f, controller.secondsPerFrame + 0.1f);
            }
            
            if (GUILayout.Button("+", buttonStyle, GUILayout.Width(30)))
            {
                controller.secondsPerFrame = Mathf.Max(0.1f, controller.secondsPerFrame - 0.1f);
            }
            
            GUILayout.Space(20);
            
            // 播放控制
            if (GUILayout.Button("⏮", buttonStyle, GUILayout.Width(35)))
            {
                controller.Stop();
            }
            
            if (GUILayout.Button("⏪", buttonStyle, GUILayout.Width(35)))
            {
                controller.PreviousFrame();
            }
            
            string playPauseText = controller.IsPlaying ? "⏸" : "▶";
            if (GUILayout.Button(playPauseText, buttonStyle, GUILayout.Width(40)))
            {
                if (controller.IsPlaying)
                    controller.Pause();
                else
                    controller.Play();
            }
            
            if (GUILayout.Button("⏩", buttonStyle, GUILayout.Width(35)))
            {
                controller.NextFrame();
            }
            
            GUILayout.Space(20);
            
            // 循环开关
            string loopText = controller.loop ? "🔁" : "➡";
            if (GUILayout.Button(loopText, buttonStyle, GUILayout.Width(35)))
            {
                controller.loop = !controller.loop;
            }
            
            GUILayout.FlexibleSpace();
            GUILayout.EndHorizontal();
            
            GUILayout.EndArea();
            
            // 加载指示器
            if (controller.IsLoading)
            {
                Rect loadingRect = new Rect(Screen.width / 2 - 50, panelY - 30, 100, 25);
                GUI.Box(loadingRect, "Loading...", boxStyle);
            }
        }
        
        Texture2D MakeTexture(int width, int height, Color color)
        {
            Color[] pixels = new Color[width * height];
            for (int i = 0; i < pixels.Length; i++)
            {
                pixels[i] = color;
            }
            
            Texture2D texture = new Texture2D(width, height);
            texture.SetPixels(pixels);
            texture.Apply();
            return texture;
        }
    }
}
