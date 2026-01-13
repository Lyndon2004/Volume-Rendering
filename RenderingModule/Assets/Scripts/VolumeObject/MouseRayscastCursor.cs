using UnityEngine;

namespace UnityVolumeRendering
{
    public class MouseRaycastCursor : MonoBehaviour
    {
        [Header("Settings")]
        [Tooltip("Directly assign the Volume Object here to enable 'Inside-Out' detection.")]
        public Transform volumeTarget; 

        [Tooltip("The LayerMask for the Volume Object (If volumeTarget is not assigned)")]
        public LayerMask targetLayer = -1;

        [Tooltip("Move cursor far away when not clicking? (Simulates On/Off)")]
        public bool hideWhenReleased = true;

        [Header("Inside Behavior")]
        [Tooltip("When inside the volume, how far forward (in local normalized units 0-1) should the drill be?")]
        [Range(0.01f, 0.5f)]
        public float insideReachDistance = 0.2f;

        private void Start()
        {
            // 自动查找 VolumeTarget
            if (volumeTarget == null)
            {
                var controller = FindObjectOfType<VolumeControllerObject>();
                if (controller != null && controller.transform.childCount > 0)
                {
                    volumeTarget = controller.transform.GetChild(0);
                }
            }
        }

        private void Update()
        {
            Camera mainCam = Camera.main;
            if (mainCam == null) return;

            bool isActive = false;
            
            if (Input.GetMouseButton(0))
            {
                Ray ray = mainCam.ScreenPointToRay(Input.mousePosition);
                Vector3 hitPoint = Vector3.zero;
                bool hitFound = false;

                // --- 策略 A: 纯数学检测 (修复了内部失效问题) ---
                if (volumeTarget != null)
                {
                    // 1. 转为局部射线
                    Vector3 localRayOrigin = volumeTarget.InverseTransformPoint(ray.origin);
                    Vector3 localRayDir = volumeTarget.InverseTransformDirection(ray.direction); // 注意：这里是非归一化的方向，包含缩放信息
                    
                    UnityEngine.Ray localRay = new UnityEngine.Ray(localRayOrigin, localRayDir);

                    // 2. 定义标准立方体包围盒 (Unity Cube 默认是中心在0，边长1，即 -0.5 到 0.5)
                    Bounds localBounds = new Bounds(Vector3.zero, Vector3.one);
                    
                    // --- 关键修复：先判断是否在内部 ---
                    if (localBounds.Contains(localRayOrigin))
                    {
                        // 场景：摄像机在内部
                        // 行为：直接将光标投射到前方固定距离 (模拟拿着手电筒)
                        // 使用 localRayDir 而不是 normalized，确保距离是相对于体积缩放的
                        // insideReachDistance = 0.2 意味着投射 20% 的体积深度
                        Vector3 localTargetPos = localRayOrigin + localRayDir.normalized * insideReachDistance;
                        
                        hitPoint = volumeTarget.TransformPoint(localTargetPos);
                        hitFound = true;
                    }
                    else
                    {
                        // 场景：摄像机在外部
                        // 行为：标准的射线求交，点哪儿是哪儿
                        float enterDist;
                        if (localBounds.IntersectRay(localRay, out enterDist))
                        {
                            Vector3 localHitPoint = localRay.GetPoint(enterDist);
                            hitPoint = volumeTarget.TransformPoint(localHitPoint);
                            hitFound = true;
                        }
                    }
                }

                // --- 策略 B: 物理回退 ---
                if (!hitFound)
                {
                    UnityEngine.RaycastHit hitInfo;
                    int layerMaskInt = (int)targetLayer.value;
                    
                    if (UnityEngine.Physics.Raycast(ray, out hitInfo, 100.0f, layerMaskInt))
                    {
                        hitPoint = hitInfo.point;
                        hitFound = true;
                    }
                }

                // --- 应用 ---
                if (hitFound)
                {
                    transform.position = hitPoint;
                    isActive = true;
                }
            }

            if (!isActive && hideWhenReleased)
            {
                transform.position = Vector3.one * 9999f; 
            }
        }
    }
}