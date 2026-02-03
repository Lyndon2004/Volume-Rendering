using System.Collections.Generic;
using System.IO;
using UnityEngine;
using System.Globalization;

namespace WaterMass
{
    public static class SimpleObjLoader
    {
        public static Mesh LoadObj(string filepath)
        {
            if (!File.Exists(filepath))
            {
                Debug.LogError($"OBJ file not found: {filepath}");
                return null;
            }

            List<Vector3> vertices = new List<Vector3>();
            List<int> triangles = new List<int>();

            string[] lines = File.ReadAllLines(filepath);

            foreach (string line in lines)
            {
                if (line.StartsWith("v "))
                {
                    string[] parts = line.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);
                    // v x y z
                    if (parts.Length >= 4)
                    {
                        float x = float.Parse(parts[1], CultureInfo.InvariantCulture);
                        float y = float.Parse(parts[2], CultureInfo.InvariantCulture);
                        float z = float.Parse(parts[3], CultureInfo.InvariantCulture);
                        vertices.Add(new Vector3(x, y, z));
                    }
                }
                else if (line.StartsWith("f "))
                {
                    string[] parts = line.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);
                    // f v1 v2 v3 ...
                    // OBJ is 1-based, Mesh is 0-based
                    if (parts.Length >= 4)
                    {
                        int v1 = int.Parse(parts[1].Split('/')[0]) - 1;
                        int v2 = int.Parse(parts[2].Split('/')[0]) - 1;
                        int v3 = int.Parse(parts[3].Split('/')[0]) - 1;

                        triangles.Add(v1);
                        triangles.Add(v2);
                        triangles.Add(v3);
                    }
                }
            }

            Mesh mesh = new Mesh();
            // Up to ~65k vertices for 16-bit index buffer, otherwise use 32-bit
            if (vertices.Count > 65000)
                mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;

            mesh.vertices = vertices.ToArray();
            mesh.triangles = triangles.ToArray();
            
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();

            return mesh;
        }
    }
}
