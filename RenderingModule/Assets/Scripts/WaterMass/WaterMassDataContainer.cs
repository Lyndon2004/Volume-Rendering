using System.Collections.Generic;
using UnityEngine;
using System;

namespace WaterMass
{
    [Serializable]
    public class TrajectoryData
    {
        public int time_index;
        // JSON centroids are typically [x, y, z] arrays or objects. 
        // We will need a helper to read them if they are arrays, 
        // but for now let's assume we parse them into Vector3 manually or via a wrapper.
        public float[] centroid; 
        public int volume_voxels;
        public int max_value;

        public Vector3 GetCentroidVector()
        {
            if (centroid != null && centroid.Length >= 3)
            {
                // Unity is usually Left Handed Y-up. 
                // Our python script already tried to swap columns to match Unity (x, y, z).
                return new Vector3(centroid[0], centroid[1], centroid[2]);
            }
            return Vector3.zero;
        }
    }

    [Serializable]
    public class TrajectoryList
    {
        public List<TrajectoryData> items;
    }
}
