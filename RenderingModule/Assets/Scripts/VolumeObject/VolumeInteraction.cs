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

            // --- 1. 深度渐变逻辑 ---
            if (Input.GetMouseButton(0))
            {
                currentDepth = Mathf.MoveTowards(currentDepth, maxDigDepth, digSpeed * Time.deltaTime);
            }
            else
            {
                currentDepth = Mathf.MoveTowards(currentDepth, 0.0f, fillSpeed * Time.deltaTime);
            }

            // --- 2. 坐标与方向计算 (关键修复) ---
            
            // A. 计算 FlashlightPos (原点)
            Vector3 camLocalPos = transform.InverseTransformPoint(Camera.main.transform.position);
            Vector3 texturePos = camLocalPos + new Vector3(0.5f, 0.5f, 0.5f);

            // B. 计算 FlashlightForward (法线) - [修正缩放扭曲]
            
            // 步骤1: 获取不带缩放影响的只有旋转的逆矩阵
            // 我们不能直接用 InverseTransformDirection，因为它包含缩放。
            // 我们需要构建一个只包含旋转的矩阵，或者手动乘法。
            // 更简单的方法是：把世界空间的 CameraForward 转换到局部空间，乘以 Scale，再归一化。
            
            // 获取世界坐标系下的视线方向
            Vector3 worldForward = Camera.main.transform.forward;
            
            // 转换到局部空间 (包含缩放)
            Vector3 localDir = transform.InverseTransformDirection(worldForward);
            
            // [核心修复] : 为了在畸变的纹理空间中保持“视觉上的垂直”，
            // 我们需要对法线向量应用 "Scale 的逆平方" 或者简单的 "乘以 Scale"。
            // 在数学上，变换法线向量需要使用 "逆转置矩阵 (Inverse Transpose)"。
            // 对于非一致缩放，这是一个经典的图形学陷阱。
            
            // 简单修正方案：
            // 将局部方向乘以 LocalScale。这听起来反直觉，但在空间变换中，
            // 法线变换 N' = mat3(transpose(inverse(Model))) * N
            // 对于单纯的缩放 (Sx, Sy, Sz)，其逆转置矩阵依然是 (1/Sx, 1/Sy, 1/Sz)。
            // 
            // 但这里我们要传的是"Ray Direction"，而不是"Surface Normal"。
            // 在纹理空间，我们需要让这个方向向量 *看起来* 依然指向世界空间的前方。
            
            Vector3 scale = transform.localScale;
            Vector3 scaledLocalDir = new Vector3(
                localDir.x * scale.x,
                localDir.y * scale.y,
                localDir.z * scale.z
            );

            // 归一化
            Vector3 textureForward = scaledLocalDir.normalized;

            // --- 3. 传递给 Shader ---
            volumeMat.SetFloat("_FlashlightRadius", currentDepth); 
            volumeMat.SetVector("_FlashlightPos", texturePos);     
            volumeMat.SetVector("_FlashlightForward", textureForward); 
        }
    }
}