using UnityEngine;

namespace UnityVolumeRendering
{
    /// <summary>
    /// 确保每个 VolumeRenderedObject 拥有独立的材质实例
    /// 解决多个体渲染对象共享材质导致渲染结果相同的问题
    /// 
    /// 使用方法：将此脚本挂载到每个 VolumeRenderedObject 的子物体（带 MeshRenderer 的那个）上
    /// </summary>
    [RequireComponent(typeof(MeshRenderer))]
    [ExecuteInEditMode]
    public class EnsureUniqueMaterial : MonoBehaviour
    {
        private MeshRenderer meshRenderer;
        private bool materialCreated = false;

        void Awake()
        {
            EnsureUniqueMaterialInstance();
        }

        void Start()
        {
            EnsureUniqueMaterialInstance();
        }

        void OnEnable()
        {
            EnsureUniqueMaterialInstance();
        }

        /// <summary>
        /// 确保材质是独立实例
        /// </summary>
        public void EnsureUniqueMaterialInstance()
        {
            if (materialCreated) return;
            
            meshRenderer = GetComponent<MeshRenderer>();
            if (meshRenderer == null) return;

            // 检查是否有材质
            if (meshRenderer.sharedMaterial == null) return;

            // 创建独立的材质实例
            // 使用 material 属性会自动创建实例，但我们显式创建以便更好控制
            Material uniqueMat = new Material(meshRenderer.sharedMaterial);
            uniqueMat.name = meshRenderer.sharedMaterial.name + "_" + gameObject.GetInstanceID();
            meshRenderer.material = uniqueMat;
            
            materialCreated = true;
            Debug.Log($"✓ 为 {transform.parent?.name ?? gameObject.name} 创建了独立材质: {uniqueMat.name}");
        }

        /// <summary>
        /// 强制重新绑定数据纹理（在数据更新后调用）
        /// </summary>
        public void RefreshDataTexture()
        {
            var volObj = GetComponentInParent<VolumeRenderedObject>();
            if (volObj != null && volObj.dataset != null && meshRenderer != null)
            {
                meshRenderer.material.SetTexture("_DataTex", volObj.dataset.GetDataTexture());
                Debug.Log($"✓ 已刷新 {volObj.name} 的数据纹理");
            }
        }
    }
}
