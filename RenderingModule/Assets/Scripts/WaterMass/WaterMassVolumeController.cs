using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace UnityVolumeRendering
{
    /// <summary>
    /// 水团体积渲染控制器
    /// 管理时间序列的加载、播放和显示
    /// </summary>
    public class WaterMassVolumeController : MonoBehaviour
    {
        [Header("=== 数据配置 ===")]
        [Tooltip("水团数据文件夹路径（相对于 StreamingAssets 或绝对路径）")]
        public string dataFolderPath = "WaterMassHighlighted";
        
        [Tooltip("文件名模式，{0} 会被替换为帧索引")]
        public string filePattern = "water_mass_highlighted_t{0}.raw";
        
        [Tooltip("总帧数")]
        public int totalFrames = 30;
        
        [Header("=== 播放控制 ===")]
        [Tooltip("每帧持续时间（秒）")]
        [Range(0.1f, 5.0f)]
        public float secondsPerFrame = 1.0f;
        
        [Tooltip("是否自动播放")]
        public bool autoPlay = false;
        
        [Tooltip("是否循环播放")]
        public bool loop = true;
        
        [Header("=== Transfer Function ===")]
        [Tooltip("水团专用 Transfer Function 文件")]
        public TransferFunction customTransferFunction;
        
        [Header("=== 引用 ===")]
        [Tooltip("体积渲染对象（留空则自动查找）")]
        public VolumeRenderedObject volumeRenderedObject;
        
        [Header("=== 加载设置 ===")]
        [Tooltip("使用同步加载（更稳定但会卡顿）")]
        public bool useSyncLoading = true;
        
        [Header("=== 运行时状态 ===")]
        [SerializeField] private int currentFrame = 0;
        [SerializeField] private bool isPlaying = false;
        [SerializeField] private bool isLoading = false;
        
        // 内部变量
        private VolumeDataset[] cachedDatasets;
        private string resolvedDataPath;
        private float playbackTimer = 0f;
        
        // 事件
        public System.Action<int> OnFrameChanged;
        public System.Action<bool> OnPlayStateChanged;
        
        #region Unity Lifecycle
        
        void Start()
        {
            Initialize();
        }
        
        void Update()
        {
            HandleInput();
            
            if (isPlaying)
            {
                if (isLoading)
                {
                    // 等待加载完成，不推进播放
                }
                else
                {
                    UpdatePlayback();
                }
            }
        }
        
        void OnGUI()
        {
            DrawInfoPanel();
        }
        
        #endregion
        
        #region Initialization
        
        void Initialize()
        {
            // 解析数据路径
            ResolveDataPath();
            
            // 查找 VolumeRenderedObject
            if (volumeRenderedObject == null)
            {
                volumeRenderedObject = FindObjectOfType<VolumeRenderedObject>();
            }
            
            if (volumeRenderedObject == null)
            {
                Debug.LogWarning("[WaterMass] No VolumeRenderedObject found. Please assign one or create from data.");
                return;
            }
            
            // 初始化缓存数组
            cachedDatasets = new VolumeDataset[totalFrames];
            
            // 如果 VolumeRenderedObject 已经有 dataset，将其作为第一帧缓存
            if (volumeRenderedObject.dataset != null)
            {
                cachedDatasets[0] = volumeRenderedObject.dataset;
                Debug.Log("[WaterMass] Using existing dataset as frame 0");
            }
            else
            {
                // 加载第一帧
                StartCoroutine(LoadFrameAsync(0, true));
            }
            
            // 确保 isLoading 初始为 false
            isLoading = false;
            
            // 应用 Transfer Function
            if (customTransferFunction != null)
            {
                ApplyTransferFunction(customTransferFunction);
            }
            
            // 自动播放
            if (autoPlay)
            {
                Play();
            }
            
            Debug.Log($"[WaterMass] Initialized. Data path: {resolvedDataPath}, Frames: {totalFrames}");
        }
        
        void ResolveDataPath()
        {
            // 尝试多种路径
            string[] possiblePaths = new string[]
            {
                // 绝对路径
                dataFolderPath,
                // StreamingAssets
                Path.Combine(Application.streamingAssetsPath, dataFolderPath),
                // Assets 目录
                Path.Combine(Application.dataPath, dataFolderPath),
                // 项目目录
                Path.Combine(Directory.GetParent(Application.dataPath).FullName, "Assets", dataFolderPath)
            };
            
            foreach (string path in possiblePaths)
            {
                if (Directory.Exists(path))
                {
                    resolvedDataPath = path;
                    return;
                }
            }
            
            // 默认使用 Assets/WaterMassHighlighted
            resolvedDataPath = Path.Combine(Application.dataPath, "WaterMassHighlighted");
            Debug.LogWarning($"[WaterMass] Data folder not found, using default: {resolvedDataPath}");
        }
        
        #endregion
        
        #region Frame Loading
        
        IEnumerator LoadFrameAsync(int frameIndex, bool switchToFrame)
        {
            Debug.Log($"[WaterMass] LoadFrameAsync started for frame {frameIndex}");
            
            if (frameIndex < 0 || frameIndex >= totalFrames)
            {
                Debug.LogError($"[WaterMass] Invalid frame index: {frameIndex}");
                yield break;
            }
            
            // 检查缓存
            if (cachedDatasets[frameIndex] != null)
            {
                Debug.Log($"[WaterMass] Frame {frameIndex} found in cache, switching...");
                if (switchToFrame)
                {
                    SwitchToFrame(frameIndex);
                }
                yield break;
            }
            
            isLoading = true;
            
            // 构建文件路径
            string fileName = string.Format(filePattern, frameIndex);
            string filePath = Path.Combine(resolvedDataPath, fileName);
            Debug.Log($"[WaterMass] Looking for file: {filePath}");
            
            if (!File.Exists(filePath))
            {
                Debug.LogError($"[WaterMass] File not found: {filePath}");
                isLoading = false;
                yield break;
            }
            
            // 读取 .ini 文件获取维度信息
            string iniPath = filePath + ".ini";
            DatasetIniData iniData = DatasetIniReader.ParseIniFile(iniPath);
            
            if (iniData == null)
            {
                Debug.LogError($"[WaterMass] INI file not found or invalid: {iniPath}");
                isLoading = false;
                yield break;
            }
            
            Debug.Log($"[WaterMass] INI loaded: {iniData.dimX}x{iniData.dimY}x{iniData.dimZ}");
            
            // 创建导入器
            RawDatasetImporter importer = new RawDatasetImporter(
                filePath,
                iniData.dimX,
                iniData.dimY,
                iniData.dimZ,
                iniData.format,
                iniData.endianness,
                iniData.bytesToSkip
            );
            
            // 异步加载
            Debug.Log($"[WaterMass] Starting import...");
            VolumeDataset dataset = null;
            yield return StartCoroutine(LoadDatasetCoroutine(importer, (result) => dataset = result));
            
            Debug.Log($"[WaterMass] Import finished, dataset is {(dataset != null ? "valid" : "null")}");
            
            if (dataset != null)
            {
                dataset.datasetName = $"WaterMass_Frame_{frameIndex}";
                cachedDatasets[frameIndex] = dataset;
                
                if (switchToFrame)
                {
                    SwitchToFrame(frameIndex);
                }
                
                Debug.Log($"[WaterMass] Loaded frame {frameIndex}");
            }
            
            isLoading = false;
        }
        
        IEnumerator LoadDatasetCoroutine(RawDatasetImporter importer, System.Action<VolumeDataset> callback)
        {
            VolumeDataset dataset = null;
            
            if (useSyncLoading)
            {
                // 同步加载 - 更稳定
                try
                {
                    dataset = importer.Import();
                    Debug.Log("[WaterMass] Sync import completed");
                }
                catch (System.Exception ex)
                {
                    Debug.LogError($"[WaterMass] Sync import error: {ex.Message}");
                }
                yield return null; // 让出一帧
            }
            else
            {
                // 异步加载 - 可能有兼容性问题
                System.Exception error = null;
                bool done = false;
                
                System.Threading.Tasks.Task.Run(() =>
                {
                    try
                    {
                        dataset = importer.Import();
                    }
                    catch (System.Exception ex)
                    {
                        error = ex;
                    }
                    finally
                    {
                        done = true;
                    }
                });
                
                float timeout = 30f;
                float elapsed = 0f;
                while (!done && elapsed < timeout)
                {
                    elapsed += Time.deltaTime;
                    yield return null;
                }
                
                if (!done)
                {
                    Debug.LogError("[WaterMass] Import timed out after 30 seconds!");
                }
                else if (error != null)
                {
                    Debug.LogError($"[WaterMass] Import error: {error.Message}\n{error.StackTrace}");
                }
            }
            
            callback?.Invoke(dataset);
        }
        
        void SwitchToFrame(int frameIndex)
        {
            if (cachedDatasets == null || cachedDatasets[frameIndex] == null)
            {
                Debug.LogWarning($"[WaterMass] Frame {frameIndex} not loaded yet");
                return;
            }
            
            currentFrame = frameIndex;
            
            // 更新 VolumeRenderedObject 的 dataset 和材质纹理
            if (volumeRenderedObject != null)
            {
                VolumeDataset newDataset = cachedDatasets[frameIndex];
                volumeRenderedObject.dataset = newDataset;
                
                // 关键：直接更新材质的 3D 纹理
                MeshRenderer meshRenderer = volumeRenderedObject.meshRenderer;
                if (meshRenderer != null && meshRenderer.sharedMaterial != null)
                {
                    Texture3D dataTexture = newDataset.GetDataTexture();
                    if (dataTexture != null)
                    {
                        meshRenderer.sharedMaterial.SetTexture("_DataTex", dataTexture);
                        Debug.Log($"[WaterMass] ✓ Switched to frame {frameIndex}, texture size: {dataTexture.width}x{dataTexture.height}x{dataTexture.depth}");
                    }
                    else
                    {
                        Debug.LogError($"[WaterMass] ✗ Frame {frameIndex} texture is null!");
                    }
                }
                else
                {
                    Debug.LogError($"[WaterMass] ✗ meshRenderer or material is null!");
                }
            }
            else
            {
                Debug.LogError("[WaterMass] ✗ volumeRenderedObject is null!");
            }
            
            OnFrameChanged?.Invoke(frameIndex);
        }
        
        #endregion
        
        #region Playback Control
        
        public void Play()
        {
            isPlaying = true;
            playbackTimer = 0f;
            OnPlayStateChanged?.Invoke(true);
            Debug.Log("[WaterMass] Playback started");
        }
        
        public void Pause()
        {
            isPlaying = false;
            OnPlayStateChanged?.Invoke(false);
            Debug.Log("[WaterMass] Playback paused");
        }
        
        public void Stop()
        {
            isPlaying = false;
            currentFrame = 0;
            playbackTimer = 0f;
            StartCoroutine(LoadFrameAsync(0, true));
            OnPlayStateChanged?.Invoke(false);
            Debug.Log("[WaterMass] Playback stopped");
        }
        
        public void NextFrame()
        {
            int nextFrame = (currentFrame + 1) % totalFrames;
            StartCoroutine(LoadFrameAsync(nextFrame, true));
        }
        
        public void PreviousFrame()
        {
            int prevFrame = (currentFrame - 1 + totalFrames) % totalFrames;
            StartCoroutine(LoadFrameAsync(prevFrame, true));
        }
        
        public void GoToFrame(int frameIndex)
        {
            frameIndex = Mathf.Clamp(frameIndex, 0, totalFrames - 1);
            StartCoroutine(LoadFrameAsync(frameIndex, true));
        }
        
        void UpdatePlayback()
        {
            playbackTimer += Time.deltaTime;
            
            if (playbackTimer >= secondsPerFrame)
            {
                playbackTimer = 0f;
                
                int nextFrame = currentFrame + 1;
                Debug.Log($"[WaterMass] Advancing from frame {currentFrame} to {nextFrame}");
                
                if (nextFrame >= totalFrames)
                {
                    if (loop)
                    {
                        nextFrame = 0;
                    }
                    else
                    {
                        Pause();
                        return;
                    }
                }
                
                StartCoroutine(LoadFrameAsync(nextFrame, true));
            }
        }
        
        #endregion
        
        #region Input Handling
        
        void HandleInput()
        {
            // P 键：播放/暂停
            if (Input.GetKeyDown(KeyCode.P))
            {
                if (isPlaying)
                    Pause();
                else
                    Play();
            }
            
            // 左右方括号：切换帧
            if (Input.GetKeyDown(KeyCode.RightBracket))
            {
                NextFrame();
            }
            
            if (Input.GetKeyDown(KeyCode.LeftBracket))
            {
                PreviousFrame();
            }
            
            // Backspace 键：重置到第一帧
            if (Input.GetKeyDown(KeyCode.Backspace))
            {
                Stop();
            }
            
            // 数字键：快速跳转
            for (int i = 0; i <= 9; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha0 + i))
                {
                    int targetFrame = i * totalFrames / 10;
                    GoToFrame(targetFrame);
                }
            }
            
            // +/- 键：调整播放速度
            if (Input.GetKeyDown(KeyCode.Equals) || Input.GetKeyDown(KeyCode.Plus))
            {
                secondsPerFrame = Mathf.Max(0.1f, secondsPerFrame - 0.1f);
            }
            
            if (Input.GetKeyDown(KeyCode.Minus))
            {
                secondsPerFrame = Mathf.Min(5.0f, secondsPerFrame + 0.1f);
            }
        }
        
        #endregion
        
        #region Transfer Function
        
        public void ApplyTransferFunction(TransferFunction tf)
        {
            if (volumeRenderedObject != null && tf != null)
            {
                volumeRenderedObject.transferFunction = tf;
                volumeRenderedObject.SetTransferFunctionMode(TFRenderMode.TF1D);
                Debug.Log("[WaterMass] Applied custom Transfer Function");
            }
        }
        
        public void LoadTransferFunctionFromFile(string tfPath)
        {
            if (File.Exists(tfPath))
            {
                TransferFunction tf = TransferFunctionDatabase.LoadTransferFunction(tfPath);
                if (tf != null)
                {
                    customTransferFunction = tf;
                    ApplyTransferFunction(tf);
                }
            }
        }
        
        #endregion
        
        #region GUI
        
        void DrawInfoPanel()
        {
            // 信息面板
            GUIStyle boxStyle = new GUIStyle(GUI.skin.box);
            boxStyle.fontSize = 14;
            
            GUIStyle labelStyle = new GUIStyle(GUI.skin.label);
            labelStyle.fontSize = 12;
            labelStyle.normal.textColor = Color.white;
            
            GUILayout.BeginArea(new Rect(10, 10, 300, 180));
            GUILayout.BeginVertical(boxStyle);
            
            GUILayout.Label("🌊 Water Mass Tracking", new GUIStyle(labelStyle) { fontSize = 16, fontStyle = FontStyle.Bold });
            GUILayout.Space(5);
            
            GUILayout.Label($"Frame: {currentFrame + 1} / {totalFrames}", labelStyle);
            GUILayout.Label($"Status: {(isLoading ? "Loading..." : (isPlaying ? "▶ Playing" : "⏸ Paused"))}", labelStyle);
            GUILayout.Label($"Speed: {1.0f / secondsPerFrame:F1} fps", labelStyle);
            
            GUILayout.Space(10);
            GUILayout.Label("Controls:", new GUIStyle(labelStyle) { fontStyle = FontStyle.Bold });
            GUILayout.Label("P: Play/Pause | [ ]: Prev/Next", labelStyle);
            GUILayout.Label("Backspace: Reset | +/-: Speed", labelStyle);
            
            GUILayout.EndVertical();
            GUILayout.EndArea();
        }
        
        #endregion
        
        #region Public API
        
        public int CurrentFrame => currentFrame;
        public int TotalFrames => totalFrames;
        public bool IsPlaying => isPlaying;
        public bool IsLoading => isLoading;
        
        /// <summary>
        /// 预加载所有帧到内存
        /// </summary>
        public void PreloadAllFrames()
        {
            StartCoroutine(PreloadAllFramesCoroutine());
        }
        
        IEnumerator PreloadAllFramesCoroutine()
        {
            Debug.Log("[WaterMass] Preloading all frames...");
            
            for (int i = 0; i < totalFrames; i++)
            {
                if (cachedDatasets[i] == null)
                {
                    yield return StartCoroutine(LoadFrameAsync(i, false));
                }
            }
            
            Debug.Log("[WaterMass] All frames preloaded");
        }
        
        /// <summary>
        /// 清理缓存释放内存
        /// </summary>
        public void ClearCache()
        {
            for (int i = 0; i < cachedDatasets.Length; i++)
            {
                if (cachedDatasets[i] != null)
                {
                    Destroy(cachedDatasets[i]);
                    cachedDatasets[i] = null;
                }
            }
            
            System.GC.Collect();
            Debug.Log("[WaterMass] Cache cleared");
        }
        
        #endregion
    }
}
