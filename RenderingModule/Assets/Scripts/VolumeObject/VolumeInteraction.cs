using UnityEngine;

namespace UnityVolumeRendering
{
    [RequireComponent(typeof(MeshRenderer))]
    public class VolumeInteraction : MonoBehaviour
    {
        [Header("Laser Drill Settings")]
        [Tooltip("Maximum depth the drill can reach.")]
        [Range(0.0f, 2.0f)]
        public float maxDigDepth = 1.0f;

        [Tooltip("Speed at which the hole deepens (units per second).")]
        [Range(0.1f, 5.0f)]
        public float digSpeed = 1.0f;

        [Tooltip("Speed at which the hole closes when released.")]
        [Range(0.1f, 10.0f)]
        public float fillSpeed = 2.0f;

        private float currentDepth = 0.0f;
        private Material volumeMat;

        private void Start()
        {
            MeshRenderer meshRenderer = GetComponent<MeshRenderer>();
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
            if (volumeMat == null || Camera.main == null) return;

            // --- 1. 深度控制逻辑 (修改部分) ---
            
            if (Input.GetMouseButton(0))
            {
                // [左键按下]：挖掘，深度趋向最大值
                currentDepth = Mathf.MoveTowards(currentDepth, maxDigDepth, digSpeed * Time.deltaTime);
            }
            else if (Input.GetMouseButton(1))
            {
                // [右键按下]：暂停/冻结
                // 此时不执行任何 MoveTowards 操作，currentDepth 保持上一帧的数值不变
                // 效果：洞停留在当前深度，不恢复也不加深
            }
            else
            {
                // [两键均未按]：回填，深度趋向 0
                currentDepth = Mathf.MoveTowards(currentDepth, 0.0f, fillSpeed * Time.deltaTime);
            }

            // --- 2. 坐标与方向计算 (保留缩放修复) ---
            
            // A. 计算 FlashlightPos (原点)
            Vector3 camLocalPos = transform.InverseTransformPoint(Camera.main.transform.position);
            Vector3 texturePos = camLocalPos + new Vector3(0.5f, 0.5f, 0.5f);

            // B. 计算 FlashlightForward (法线)
            Vector3 worldForward = Camera.main.transform.forward;
            Vector3 localDir = transform.InverseTransformDirection(worldForward);
            
            // 修正非均匀缩放导致的角度畸变
            Vector3 scale = transform.localScale;
            Vector3 scaledLocalDir = new Vector3(
                localDir.x * scale.x,
                localDir.y * scale.y,
                localDir.z * scale.z
            );

            Vector3 textureForward = scaledLocalDir.normalized;

            // --- 3. 传递给 Shader ---
            volumeMat.SetFloat("_FlashlightRadius", currentDepth); 
            volumeMat.SetVector("_FlashlightPos", texturePos);     
            volumeMat.SetVector("_FlashlightForward", textureForward); 
        }
    }
}