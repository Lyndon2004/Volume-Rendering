using UnityEngine;
using UnityEditor;
using System.IO;

namespace UnityVolumeRendering
{
    /// <summary>
    /// 水团可视化编辑器窗口
    /// 提供快速创建和配置水团可视化的工具
    /// </summary>
    public class WaterMassEditorWindow : EditorWindow
    {
        private string dataFolderPath = "";
        private int totalFrames = 30;
        private float playbackSpeed = 1.0f;
        private bool autoPlay = false;
        private bool preloadAll = false;
        
        private TransferFunction selectedTF;
        private VolumeRenderedObject existingVolumeObject;
        
        [MenuItem("Volume Rendering/Water Mass Tracking/Setup Window", priority = 100)]
        public static void ShowWindow()
        {
            WaterMassEditorWindow window = GetWindow<WaterMassEditorWindow>();
            window.titleContent = new GUIContent("Water Mass Setup");
            window.minSize = new Vector2(400, 450);
            window.Show();
        }
        
        void OnEnable()
        {
            // 自动检测数据路径
            string defaultPath = Path.Combine(Application.dataPath, "WaterMassHighlighted");
            if (Directory.Exists(defaultPath))
            {
                dataFolderPath = defaultPath;
                DetectFrameCount();
            }
            
            // 查找现有的 VolumeRenderedObject
            existingVolumeObject = FindObjectOfType<VolumeRenderedObject>();
        }
        
        void OnGUI()
        {
            EditorGUILayout.Space(10);
            EditorGUILayout.LabelField("🌊 Water Mass Tracking Setup", EditorStyles.boldLabel);
            EditorGUILayout.Space(10);
            
            DrawDataSection();
            EditorGUILayout.Space(10);
            
            DrawPlaybackSection();
            EditorGUILayout.Space(10);
            
            DrawTransferFunctionSection();
            EditorGUILayout.Space(10);
            
            DrawVolumeObjectSection();
            EditorGUILayout.Space(20);
            
            DrawActionButtons();
        }
        
        void DrawDataSection()
        {
            EditorGUILayout.LabelField("Data Configuration", EditorStyles.boldLabel);
            EditorGUILayout.BeginVertical("box");
            
            // 数据文件夹
            EditorGUILayout.BeginHorizontal();
            dataFolderPath = EditorGUILayout.TextField("Data Folder", dataFolderPath);
            if (GUILayout.Button("Browse", GUILayout.Width(60)))
            {
                string selected = EditorUtility.OpenFolderPanel("Select Water Mass Data Folder", Application.dataPath, "");
                if (!string.IsNullOrEmpty(selected))
                {
                    dataFolderPath = selected;
                    DetectFrameCount();
                }
            }
            EditorGUILayout.EndHorizontal();
            
            // 帧数
            totalFrames = EditorGUILayout.IntField("Total Frames", totalFrames);
            
            // 检测状态
            if (!string.IsNullOrEmpty(dataFolderPath))
            {
                int detectedFrames = CountFrames();
                EditorGUILayout.HelpBox($"Detected {detectedFrames} frame files in folder.", MessageType.Info);
            }
            
            EditorGUILayout.EndVertical();
        }
        
        void DrawPlaybackSection()
        {
            EditorGUILayout.LabelField("Playback Settings", EditorStyles.boldLabel);
            EditorGUILayout.BeginVertical("box");
            
            playbackSpeed = EditorGUILayout.Slider("Seconds per Frame", playbackSpeed, 0.1f, 5.0f);
            autoPlay = EditorGUILayout.Toggle("Auto Play on Start", autoPlay);
            preloadAll = EditorGUILayout.Toggle("Preload All Frames", preloadAll);
            
            if (preloadAll)
            {
                long estimatedMB = totalFrames * 16L; // ~16MB per frame
                EditorGUILayout.HelpBox($"Preloading will use ~{estimatedMB}MB of memory.", MessageType.Warning);
            }
            
            EditorGUILayout.EndVertical();
        }
        
        void DrawTransferFunctionSection()
        {
            EditorGUILayout.LabelField("Transfer Function", EditorStyles.boldLabel);
            EditorGUILayout.BeginVertical("box");
            
            selectedTF = (TransferFunction)EditorGUILayout.ObjectField("Custom TF", selectedTF, typeof(TransferFunction), false);
            
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Load from File"))
            {
                string tfPath = EditorUtility.OpenFilePanel("Select Transfer Function", Application.dataPath, "tf");
                if (!string.IsNullOrEmpty(tfPath))
                {
                    selectedTF = TransferFunctionDatabase.LoadTransferFunction(tfPath);
                    if (selectedTF != null)
                    {
                        Debug.Log($"Loaded TF: {tfPath}");
                    }
                }
            }
            
            if (GUILayout.Button("Create Default"))
            {
                selectedTF = CreateDefaultWaterMassTF();
                Debug.Log("Created default Water Mass Transfer Function");
            }
            EditorGUILayout.EndHorizontal();
            
            EditorGUILayout.EndVertical();
        }
        
        void DrawVolumeObjectSection()
        {
            EditorGUILayout.LabelField("Volume Object", EditorStyles.boldLabel);
            EditorGUILayout.BeginVertical("box");
            
            existingVolumeObject = (VolumeRenderedObject)EditorGUILayout.ObjectField(
                "Existing Volume", existingVolumeObject, typeof(VolumeRenderedObject), true);
            
            if (existingVolumeObject != null)
            {
                EditorGUILayout.HelpBox("Will attach controller to existing volume object.", MessageType.Info);
            }
            else
            {
                EditorGUILayout.HelpBox("No volume object selected. Will create new one from first frame.", MessageType.Warning);
            }
            
            EditorGUILayout.EndVertical();
        }
        
        void DrawActionButtons()
        {
            EditorGUILayout.BeginHorizontal();
            
            GUI.backgroundColor = new Color(0.3f, 0.7f, 0.3f);
            if (GUILayout.Button("Create Water Mass Visualization", GUILayout.Height(40)))
            {
                CreateWaterMassVisualization();
            }
            
            GUI.backgroundColor = Color.white;
            EditorGUILayout.EndHorizontal();
            
            EditorGUILayout.Space(5);
            
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Import First Frame Only"))
            {
                ImportSingleFrame(0);
            }
            
            if (GUILayout.Button("Open Data Folder"))
            {
                if (Directory.Exists(dataFolderPath))
                {
                    EditorUtility.RevealInFinder(dataFolderPath);
                }
            }
            EditorGUILayout.EndHorizontal();
        }
        
        void CreateWaterMassVisualization()
        {
            if (string.IsNullOrEmpty(dataFolderPath) || !Directory.Exists(dataFolderPath))
            {
                EditorUtility.DisplayDialog("Error", "Please select a valid data folder.", "OK");
                return;
            }
            
            // 如果没有现有的 VolumeRenderedObject，先导入第一帧创建一个
            VolumeRenderedObject volumeObject = existingVolumeObject;
            
            if (volumeObject == null)
            {
                volumeObject = ImportSingleFrame(0);
                if (volumeObject == null)
                {
                    EditorUtility.DisplayDialog("Error", "Failed to import first frame.", "OK");
                    return;
                }
            }
            
            // 添加或获取控制器
            WaterMassVolumeController controller = volumeObject.GetComponent<WaterMassVolumeController>();
            if (controller == null)
            {
                controller = volumeObject.gameObject.AddComponent<WaterMassVolumeController>();
            }
            
            // 配置控制器
            controller.dataFolderPath = dataFolderPath;
            controller.totalFrames = totalFrames;
            controller.secondsPerFrame = playbackSpeed;
            controller.autoPlay = autoPlay;
            controller.volumeRenderedObject = volumeObject;
            
            if (selectedTF != null)
            {
                controller.customTransferFunction = selectedTF;
            }
            
            // 标记为已修改
            EditorUtility.SetDirty(controller);
            
            // 选中创建的对象
            Selection.activeGameObject = volumeObject.gameObject;
            
            Debug.Log($"[WaterMass] Created visualization with {totalFrames} frames");
            EditorUtility.DisplayDialog("Success", 
                $"Water Mass Visualization created!\n\nPress Play to test.\n\nControls:\n- Space: Play/Pause\n- ←→: Previous/Next Frame\n- R: Reset", 
                "OK");
        }
        
        VolumeRenderedObject ImportSingleFrame(int frameIndex)
        {
            string fileName = $"water_mass_highlighted_t{frameIndex}.raw";
            string filePath = Path.Combine(dataFolderPath, fileName);
            string iniPath = filePath + ".ini";
            
            if (!File.Exists(filePath))
            {
                Debug.LogError($"File not found: {filePath}");
                return null;
            }
            
            // 读取 INI 文件
            DatasetIniData iniData = DatasetIniReader.ParseIniFile(iniPath);
            if (iniData == null)
            {
                Debug.LogError($"INI file not found or invalid: {iniPath}");
                return null;
            }
            
            // 导入数据
            RawDatasetImporter importer = new RawDatasetImporter(
                filePath,
                iniData.dimX,
                iniData.dimY,
                iniData.dimZ,
                iniData.format,
                iniData.endianness,
                iniData.bytesToSkip
            );
            
            VolumeDataset dataset = importer.Import();
            if (dataset == null)
            {
                Debug.LogError("Failed to import dataset");
                return null;
            }
            
            dataset.datasetName = $"WaterMass_Frame_{frameIndex}";
            
            // 创建体积渲染对象
            VolumeRenderedObject volumeObject = VolumeObjectFactory.CreateObject(dataset);
            
            // 应用 Transfer Function
            if (selectedTF != null)
            {
                volumeObject.transferFunction = selectedTF;
                volumeObject.SetTransferFunctionMode(TFRenderMode.TF1D);
            }
            
            // 重命名
            volumeObject.gameObject.name = "WaterMassVolume";
            
            return volumeObject;
        }
        
        TransferFunction CreateDefaultWaterMassTF()
        {
            TransferFunction tf = ScriptableObject.CreateInstance<TransferFunction>();
            
            // 清空现有控制点
            tf.colourControlPoints = new System.Collections.Generic.List<TFColourControlPoint>();
            tf.alphaControlPoints = new System.Collections.Generic.List<TFAlphaControlPoint>();
            
            // 透明区域 (0 值 = 边界外)
            tf.colourControlPoints.Add(new TFColourControlPoint(0.0f, new Color(0, 0, 0, 0)));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(0.0f, 0.0f));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(0.005f, 0.0f));
            
            // 背景海洋 (1-199 归一化到 0.01-0.78)
            tf.colourControlPoints.Add(new TFColourControlPoint(0.01f, new Color(0.1f, 0.15f, 0.25f)));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(0.01f, 0.015f));
            
            tf.colourControlPoints.Add(new TFColourControlPoint(0.4f, new Color(0.15f, 0.2f, 0.35f)));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(0.4f, 0.03f));
            
            tf.colourControlPoints.Add(new TFColourControlPoint(0.78f, new Color(0.2f, 0.25f, 0.4f)));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(0.78f, 0.05f));
            
            // 水团区域 (200-255 归一化到 0.785-1.0) - 橙黄色高亮
            tf.colourControlPoints.Add(new TFColourControlPoint(0.785f, new Color(1.0f, 0.6f, 0.1f)));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(0.785f, 0.5f));
            
            tf.colourControlPoints.Add(new TFColourControlPoint(0.9f, new Color(1.0f, 0.8f, 0.2f)));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(0.9f, 0.7f));
            
            tf.colourControlPoints.Add(new TFColourControlPoint(1.0f, new Color(1.0f, 0.95f, 0.4f)));
            tf.alphaControlPoints.Add(new TFAlphaControlPoint(1.0f, 0.85f));
            
            tf.GenerateTexture();
            
            return tf;
        }
        
        void DetectFrameCount()
        {
            int count = CountFrames();
            if (count > 0)
            {
                totalFrames = count;
            }
        }
        
        int CountFrames()
        {
            if (string.IsNullOrEmpty(dataFolderPath) || !Directory.Exists(dataFolderPath))
                return 0;
            
            int count = 0;
            for (int i = 0; i < 100; i++) // 最多检查 100 帧
            {
                string fileName = $"water_mass_highlighted_t{i}.raw";
                if (File.Exists(Path.Combine(dataFolderPath, fileName)))
                {
                    count++;
                }
                else
                {
                    break;
                }
            }
            return count;
        }
        
        [MenuItem("Volume Rendering/Water Mass Tracking/Quick Import First Frame", priority = 101)]
        public static void QuickImportFirstFrame()
        {
            string defaultPath = Path.Combine(Application.dataPath, "WaterMassHighlighted");
            string filePath = Path.Combine(defaultPath, "water_mass_highlighted_t0.raw");
            
            if (!File.Exists(filePath))
            {
                filePath = EditorUtility.OpenFilePanel("Select Water Mass RAW File", Application.dataPath, "raw");
                if (string.IsNullOrEmpty(filePath)) return;
            }
            
            string iniPath = filePath + ".ini";
            DatasetIniData iniData = DatasetIniReader.ParseIniFile(iniPath);
            
            if (iniData == null)
            {
                EditorUtility.DisplayDialog("Error", "INI file not found or invalid.", "OK");
                return;
            }
            
            RawDatasetImporter importer = new RawDatasetImporter(
                filePath, iniData.dimX, iniData.dimY, iniData.dimZ,
                iniData.format, iniData.endianness, iniData.bytesToSkip
            );
            
            VolumeDataset dataset = importer.Import();
            if (dataset != null)
            {
                dataset.datasetName = "WaterMass_Quick";
                VolumeRenderedObject obj = VolumeObjectFactory.CreateObject(dataset);
                obj.gameObject.name = "WaterMassVolume_Quick";
                Selection.activeGameObject = obj.gameObject;
            }
        }
    }
}
