using UnityEngine;
using System.IO;

namespace WaterMass
{
    /// <summary>
    /// Loads and displays the ocean boundary mesh (irregular coastline shape).
    /// This provides a reference frame showing the full ocean domain.
    /// </summary>
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public class OceanBoundaryDisplay : MonoBehaviour
    {
        [Header("Boundary Mesh File")]
        [Tooltip("Leave empty to auto-detect, or enter filename like 'OceanBoundary.obj'")]
        public string boundaryMeshFileName = "OceanBoundary.obj";
        
        [Tooltip("Folder containing the mesh (relative to Assets or absolute)")]
        public string dataFolder = "WaterMassOutput";
        
        [Header("Position Offset (same as WaterMassManager)")]
        [Tooltip("Auto-sync from WaterMassManager if assigned, otherwise use this value")]
        public WaterMassManager manager; // Drag WaterMassManager here to auto-sync
        public Vector3 positionOffset = new Vector3(220f, 180f, 10f);
        
        [Header("Coordinate Transform")]
        [Tooltip("Apply 90 degree X rotation to match VolumeSTCube coordinate system")]
        public bool applyVolumeRotation = true;
        
        [Header("Appearance")]
        public Color boundaryColor = new Color(0.5f, 0.8f, 1f, 0.15f); // Light blue, very transparent
        public bool useWireframe = true;
        
        private MeshFilter mf;
        private MeshRenderer mr;
        private Mesh boundaryMesh;
        
        void Awake()
        {
            mf = GetComponent<MeshFilter>();
            mr = GetComponent<MeshRenderer>();
        }
        
        void Start()
        {
            // Sync offset from WaterMassManager if assigned
            if (manager != null)
            {
                positionOffset = manager.positionOffset;
                Debug.Log($"🔗 Synced positionOffset from WaterMassManager: {positionOffset}");
            }
            
            // Build full path
            string fullPath;
            if (Path.IsPathRooted(dataFolder))
            {
                // Absolute path provided
                fullPath = Path.Combine(dataFolder, boundaryMeshFileName);
            }
            else
            {
                // Relative to Assets folder
                fullPath = Path.Combine(Application.dataPath, dataFolder, boundaryMeshFileName);
            }
            
            Debug.Log($"🔍 Looking for ocean boundary at: {fullPath}");
            
            LoadBoundaryMesh(fullPath);
            SetupMaterial();
            
            // Apply rotation to match VolumeSTCube coordinate system
            if (applyVolumeRotation)
            {
                transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                Debug.Log("🔄 Applied 90° X rotation to match VolumeSTCube coordinates");
            }
            
            // Apply offset to bring mesh near origin (same as water mass mesh)
            transform.localPosition = -positionOffset;
            Debug.Log($"📍 Ocean boundary position set to: {transform.localPosition}");
        }
        
        void LoadBoundaryMesh(string path)
        {
            if (!File.Exists(path))
            {
                Debug.LogError($"❌ Ocean boundary mesh not found: {path}");
                return;
            }
            
            boundaryMesh = SimpleObjLoader.LoadObj(path);
            
            if (boundaryMesh != null)
            {
                mf.mesh = boundaryMesh;
                Debug.Log($"✅ Loaded ocean boundary: {boundaryMesh.vertexCount} vertices, Bounds: {boundaryMesh.bounds}");
            }
            else
            {
                Debug.LogError("❌ Failed to load ocean boundary mesh");
            }
        }
        
        void SetupMaterial()
        {
            if (useWireframe)
            {
                // Try to find a wireframe shader, otherwise use transparent
                Shader wireShader = Shader.Find("Custom/Wireframe");
                if (wireShader == null)
                {
                    // Fallback to standard transparent
                    Material mat = new Material(Shader.Find("Standard"));
                    mat.color = boundaryColor;
                    
                    // Set to transparent mode
                    mat.SetFloat("_Mode", 3);
                    mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
                    mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                    mat.SetInt("_ZWrite", 0);
                    mat.DisableKeyword("_ALPHATEST_ON");
                    mat.EnableKeyword("_ALPHABLEND_ON");
                    mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                    mat.renderQueue = 3000;
                    
                    // Enable backface culling off for see-through
                    mat.SetInt("_Cull", (int)UnityEngine.Rendering.CullMode.Off);
                    
                    mr.material = mat;
                    Debug.Log("🎨 Using transparent material for ocean boundary");
                }
                else
                {
                    Material mat = new Material(wireShader);
                    mat.color = boundaryColor;
                    mr.material = mat;
                }
            }
            else
            {
                Material mat = new Material(Shader.Find("Standard"));
                mat.color = boundaryColor;
                mat.SetFloat("_Mode", 3);
                mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
                mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                mat.SetInt("_ZWrite", 0);
                mat.renderQueue = 3000;
                mr.material = mat;
            }
        }
        
        /// <summary>
        /// Update color at runtime
        /// </summary>
        public void SetColor(Color newColor)
        {
            boundaryColor = newColor;
            if (mr != null && mr.material != null)
            {
                mr.material.color = newColor;
            }
        }
        
        /// <summary>
        /// Toggle visibility
        /// </summary>
        public void SetVisible(bool visible)
        {
            mr.enabled = visible;
        }
    }
}
