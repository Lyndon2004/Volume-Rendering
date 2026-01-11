using UnityEngine;

namespace UnityVolumeRendering
{
    [RequireComponent(typeof(MeshRenderer))]
    public class VolumeInteraction : MonoBehaviour
    {
        [Header("Interaction Target")]
        [Tooltip("Assign the Transform you want to track (e.g., VR Hand, Controller, or a debug Sphere following the mouse).")]
        public Transform target;

        private Material volumeMat;

        private void Start()
        {
            MeshRenderer meshRenderer = GetComponent<MeshRenderer>();
            
            // Getting .material creates a runtime instance, ensuring we don't modify the asset on disk
            if (meshRenderer != null)
            {
                volumeMat = meshRenderer.material;
            }
            else
            {
                Debug.LogError("VolumeInteraction: No MeshRenderer found on this GameObject!");
            }
        }

        private void Update()
        {
            // Ensure we have a valid material and target before processing
            if (volumeMat != null && target != null)
            {
                // 1. Convert the Target's World Position to the Volume's Local Position
                // This accounts for the Volume's Position, Rotation, and Scale automatically.
                Vector3 localPos = transform.InverseTransformPoint(target.position);

                // 2. Convert Local Position to Texture Coordinates (0 to 1 range)
                // Unity's default Cube mesh has local coordinates from -0.5 to 0.5.
                // Adding 0.5 shifts the range to 0.0 to 1.0, which matches the 3D Texture UVs.
                Vector3 texturePos = localPos + new Vector3(0.5f, 0.5f, 0.5f);

                // 3. Pass the calculated vector to the Shader
                // The Shader uses this to determine where to clip ("Magic Flashlight effect")
                volumeMat.SetVector("_FlashlightPos", texturePos);
            }
        }
    }
}