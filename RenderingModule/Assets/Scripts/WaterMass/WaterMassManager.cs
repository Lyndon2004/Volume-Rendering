using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.IO;
// using Newtonsoft.Json; // If NewtonSoft is available, otherwise uses JsonUtility wrapper

namespace WaterMass
{
    public class WaterMassManager : MonoBehaviour
    {
        [Header("Config")]
        public string dataFolder; // Path to folder containing json and objs
        public string trajectoryFileName = "MultiVar_WaterMass_trajectory.json";
        public string meshPrefix = "MultiVar_WaterMass_t"; // Matches python output pattern
        
        [Header("Position Offset (to bring mesh into view)")]
        [Tooltip("Offset to subtract from mesh coordinates. Set based on mesh bounds center.")]
        public Vector3 positionOffset = new Vector3(220f, 180f, 10f);
        
        [Header("References")]
        public TrajectoryRenderer trajectoryRenderer;
        public MeshSequencePlayer meshPlayer;

        private List<TrajectoryData> trajectoryData;
        private int maxTimeIndex = 0;

        void Start()
        {
            // Auto-detect path if empty, for testing
            if (string.IsNullOrEmpty(dataFolder))
            {
                // This is just a default for the sake of the script working out of box
                // User should set this in Inspector
                dataFolder = Application.dataPath + "/../DataTransformationModule/MultiVarOutput";
            }

            LoadData();
        }

        void LoadData()
        {
            string jsonPath = Path.Combine(dataFolder, trajectoryFileName);
            if (!File.Exists(jsonPath))
            {
                Debug.LogError($"Trajectory JSON not found at: {jsonPath}");
                return;
            }

            string jsonContent = File.ReadAllText(jsonPath);
            
            // Should use a robust JSON parser. 
            // Since Unity's JsonUtility has limitations with top-level arrays, 
            // we might need to wrap the python output in an object: { "items": [...] } 
            // OR use a simple helper if the format is strictly list.
            // Python output was: [ { ... }, { ... } ]
            // We can wrap it manually for JsonUtility
            string wrappedJson = "{ \"items\": " + jsonContent + "}";
            
            try
            {
                TrajectoryList data = JsonUtility.FromJson<TrajectoryList>(wrappedJson);
                trajectoryData = data.items;
            }
            catch (System.Exception e)
            {
                Debug.LogError($"JSON Parse Error: {e.Message}. Make sure JSON is valid.");
                return;
            }

            if (trajectoryData != null && trajectoryData.Count > 0)
            {
                Debug.Log($"✅ Loaded {trajectoryData.Count} trajectory points");
                
                // Log first centroid to help with positioning
                if (trajectoryData[0].centroid != null)
                {
                    Debug.Log($"📍 First centroid: ({trajectoryData[0].centroid[0]}, {trajectoryData[0].centroid[1]}, {trajectoryData[0].centroid[2]})");
                    Debug.Log($"💡 Suggested camera position: ({trajectoryData[0].centroid[0]}, {trajectoryData[0].centroid[1]}, {trajectoryData[0].centroid[2] - 100f})");
                }
                
                // Init Systems
                trajectoryRenderer.InitializePath(trajectoryData);
                
                meshPlayer.meshFolderAbsolute = dataFolder;
                meshPlayer.filePrefix = meshPrefix;

                maxTimeIndex = trajectoryData.Count - 1;
                
                // Apply offset to the mesh container
                if (meshPlayer != null)
                {
                    meshPlayer.transform.localPosition = -positionOffset;
                    Debug.Log($"🔧 Applied position offset: {-positionOffset} to mesh container");
                }
                
                // Start at time 0
                SetTime(0);
            }
        }

        // Public API for UI Slider
        // timeNormalized: 0.0 to 1.0
        public void OnTimeSliderChanged(float timeNormalized)
        {
            if (maxTimeIndex == 0) return;
            
            int targetIndex = Mathf.RoundToInt(timeNormalized * maxTimeIndex);
            SetTime(targetIndex);
        }

        public void SetTime(int timeIndex)
        {
            if (trajectoryData == null) return;
            
            // Clamp
            timeIndex = Mathf.Clamp(timeIndex, 0, maxTimeIndex);

            // Update Mesh
            meshPlayer.SetMesh(timeIndex);

            // Update Trajectory Line (grow up to current time)
            trajectoryRenderer.UpdateProgress(timeIndex);
            
            // Here you would also update the 2D UI Chart
            // UIChart.Highlight(timeIndex, trajectoryData[timeIndex].volume_voxels);
        }
    }
}
