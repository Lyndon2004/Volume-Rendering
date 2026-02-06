using System.Collections.Generic;
using UnityEngine;

namespace WaterMass
{
    [RequireComponent(typeof(LineRenderer))]
    public class TrajectoryRenderer : MonoBehaviour
    {
        private LineRenderer lr;
        private List<Vector3> fullPath = new List<Vector3>();

        public Color startColor = Color.blue;
        public Color endColor = Color.red;
        
        [Tooltip("Position offset to align with mesh (set same as WaterMassManager offset)")]
        public Vector3 positionOffset = new Vector3(220f, 180f, 10f);
        
        [Tooltip("Apply coordinate transform to match VolumeSTCube (swap Y and Z)")]
        public bool applyVolumeCoordTransform = true;

        void Awake()
        {
            lr = GetComponent<LineRenderer>();
            lr.useWorldSpace = true; // Typically we draw in world space
            lr.startWidth = 1.0f; // Adjustable
            lr.endWidth = 1.0f;
            
            // Set Gradient
            Gradient gradient = new Gradient();
            gradient.SetKeys(
                new GradientColorKey[] { new GradientColorKey(startColor, 0.0f), new GradientColorKey(endColor, 1.0f) },
                new GradientAlphaKey[] { new GradientAlphaKey(1.0f, 0.0f), new GradientAlphaKey(1.0f, 1.0f) }
            );
            lr.colorGradient = gradient;
        }

        public void InitializePath(List<TrajectoryData> dataList)
        {
            fullPath.Clear();
            foreach (var item in dataList)
            {
                // Assuming item.GetCentroidVector() returns the correct world position
                // or local position relative to the volume container. 
                // If relative, we might need to transform it. For now, assuming direct mapping.
                if (item.centroid != null)
                {
                    // Get raw centroid
                    Vector3 rawPoint = item.GetCentroidVector();
                    
                    // Apply coordinate transform to match VolumeSTCube (90° X rotation = swap Y and Z)
                    Vector3 point;
                    if (applyVolumeCoordTransform)
                    {
                        // After 90° X rotation: (x, y, z) -> (x, -z, y)
                        // But since our data is already in data space, we need: (x, y, z) -> (x, z, y)
                        point = new Vector3(rawPoint.x - positionOffset.x, 
                                           rawPoint.z - positionOffset.z,  // Z becomes Y
                                           rawPoint.y - positionOffset.y); // Y becomes Z
                    }
                    else
                    {
                        point = rawPoint - positionOffset;
                    }
                    
                    fullPath.Add(point);
                    Debug.Log($"📍 Trajectory point {item.time_index}: raw={rawPoint}, transformed={point}");
                }
                else
                {
                    // If visual gap is needed for missing data, logic goes here
                    // For now, simple connection
                }
            }
            
            Debug.Log($"✅ Trajectory initialized with {fullPath.Count} points");
            
            // Draw full path initially? Or none?
            // Usually we show the path up to current time.
            lr.positionCount = 0;
        }

        public void UpdateProgress(int currentIndex)
        {
            if (fullPath.Count == 0 || currentIndex < 0) return;

            // Clamp index
            int endNode = Mathf.Min(currentIndex + 1, fullPath.Count);
            
            lr.positionCount = endNode;
            for (int i = 0; i < endNode; i++)
            {
                lr.SetPosition(i, fullPath[i]);
            }
        }
    }
}
