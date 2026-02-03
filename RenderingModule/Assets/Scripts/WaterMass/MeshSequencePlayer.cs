using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.IO;

namespace WaterMass
{
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public class MeshSequencePlayer : MonoBehaviour
    {
        public string meshFolderAbsolute; // Absolute path to ease testing, or relative to StreamingAssets
        public string filePrefix = "WaterMass_t";
        public string fileExtension = ".obj";
        
        [Header("Material Settings")]
        public Color meshColor = new Color(0.2f, 0.6f, 0.9f, 0.7f); // Light blue, semi-transparent
        
        // Cache to store loaded meshes (be careful with memory for huge datasets)
        private Dictionary<int, Mesh> meshCache = new Dictionary<int, Mesh>();
        
        // Simple Least Recently Used (LRU) or Window buffer could be implemented here
        // For now, we cache everything or just simple load on demand.
        // Let's implement a simple direct loader with basic caching.

        private MeshFilter mf;
        private MeshRenderer mr;

        void Awake()
        {
            mf = GetComponent<MeshFilter>();
            mr = GetComponent<MeshRenderer>();
            
            // Ensure we have a material
            EnsureMaterial();
        }
        
        void EnsureMaterial()
        {
            if (mr.sharedMaterial == null)
            {
                // Create a default material if none assigned
                Material defaultMat = new Material(Shader.Find("Standard"));
                defaultMat.color = meshColor;
                
                // Enable transparency
                defaultMat.SetFloat("_Mode", 3); // Transparent mode
                defaultMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
                defaultMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                defaultMat.SetInt("_ZWrite", 0);
                defaultMat.DisableKeyword("_ALPHATEST_ON");
                defaultMat.EnableKeyword("_ALPHABLEND_ON");
                defaultMat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                defaultMat.renderQueue = 3000;
                
                mr.material = defaultMat;
                Debug.Log("🎨 Created default transparent material for mesh");
            }
        }

        public void SetMesh(int timeIndex)
        {
            if (meshCache.ContainsKey(timeIndex))
            {
                mf.mesh = meshCache[timeIndex];
                return;
            }

            // Try load
            string filename = $"{filePrefix}{timeIndex}{fileExtension}";
            string path = Path.Combine(meshFolderAbsolute, filename);

            if (File.Exists(path))
            {
                // In a real high-perf scenario, this should be async or threaded
                Mesh m = SimpleObjLoader.LoadObj(path);
                if (m != null)
                {
                    meshCache[timeIndex] = m;
                    mf.mesh = m;
                    Debug.Log($"✅ Loaded mesh: {filename}, Vertices: {m.vertexCount}, Bounds: {m.bounds}");
                }
                else
                {
                    Debug.LogWarning($"Failed to load mesh: {path}");
                    mf.mesh = null; // Hide if missing
                }
            }
            else
            {
                Debug.LogWarning($"Mesh file not found: {path}");
                // No mesh for this frame (maybe empty water mass)
                mf.mesh = null;
            }
        }
        
        public void ClearCache()
        {
            meshCache.Clear();
        }
    }
}
