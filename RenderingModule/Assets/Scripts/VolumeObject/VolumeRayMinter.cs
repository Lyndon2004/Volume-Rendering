using UnityEngine;

namespace UnityVolumeRendering
{
    /// <summary>
    /// 实现“动态近裁剪”效果：
    /// 1. 透明中心锁定在摄像机位置。
    /// 2. 按住左键增大半径 = 增大能看清深度的距离（推开眼前的遮挡）。
    /// </summary>
    [RequireComponent(typeof(VolumeControllerObject))]
    public class VolumeRayMinter : MonoBehaviour
    {
        [Header("Settings")]
        [Tooltip("推进速度 (sensitivity)")]
        public float growSpeed = 0.2f;

        [Tooltip("最大深度 (0.0 - 2.0)")]
        public float maxRadius = 1.5f;

        // 当前的"透明距离"
        private float currentRadius = 0.0f;
        private VolumeControllerObject controller;
        private Transform volumeTransform;
        
        private void Start()
        {
            controller = GetComponent<VolumeControllerObject>();
            if (controller != null && controller.volumeContainerObjects.Length > 0)
            {
                var volObj = controller.volumeContainerObjects[0];
                if (volObj != null)
                {
                    volumeTransform = volObj.transform;
                }
            }
        }

        private void LateUpdate()
        {
            if (controller == null || volumeTransform == null) return;

            Camera cam = Camera.main;
            if (cam == null) return;

            // 1. 交互
            if (Input.GetMouseButton(0)) currentRadius += growSpeed * Time.deltaTime;
            else if (Input.GetMouseButton(1)) currentRadius -= growSpeed * Time.deltaTime;
            currentRadius = Mathf.Clamp(currentRadius, 0.0f, maxRadius);

            // 2. 计算位置 (纹理空间)
            Vector3 camLocalPos = volumeTransform.InverseTransformPoint(cam.transform.position);
            Vector3 camTexPos = camLocalPos + new Vector3(0.5f, 0.5f, 0.5f);

            // 3. 关键修复：计算视线的"局部方向" (Local Forward)
            // 这让 Shader 能切出平面，而不是球体
            // InverseTransformDirection 会处理旋转，但保持相对方向
            Vector3 localForward = volumeTransform.InverseTransformDirection(cam.transform.forward);
            
            // 为了保证切面在非均匀缩放(如扁平物体)下依然垂直于视线，
            // 这里我们不做 normalize，或者根据需求保留其缩放特性
            // 但为了 Shader 计算的稳定性，我们通常传归一化的方向用于 Dot 计算
            Vector3 camForwardTex = localForward.normalized; 

            // 4. 更新 Shader
            // 我们复用 _FlashlightPos (传位置)
            // 并利用 _CircleDensity (或者其他不用的变量) 来传 Forward 向量? 
            // 不，最稳妥的是新增一个变量，但为了不改 Shader 定义，我们这里使用一个小技巧：
            // 将 Forward 向量打包进一个新的 Vector 属性，或者就用 _FlashlightPos 的 w 分量存一点信息?
            // 鉴于您之前的 Shader 定义，我们最好直接加一个 SetVector("_CamLookDir")
            
            for (int i = 0; i < controller.meshRenderers.Length; i++)
            {
                Material mat = controller.meshRenderers[i].sharedMaterial;
                if (mat != null)
                {
                    mat.SetVector("_FlashlightPos", camTexPos);       // 眼睛位置
                    mat.SetVector("_FlashlightForward", camForwardTex); // 眼睛朝向 [新增]
                    mat.SetFloat("_FlashlightRadius", currentRadius); // 切割深度
                }
            }
        }
    }
}