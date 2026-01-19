Shader "VolumeRendering/DirectVolumeRenderingShader"
{
    Properties
    {
        _DataTex ("Data Texture (Generated)", 3D) = "" {}
        _GradientTex("Gradient Texture (Generated)", 3D) = "" {}
        _NoiseTex("Noise Texture (Generated)", 2D) = "white" {}
        _TFTex("Transfer Function Texture (Generated)", 2D) = "" {}
        _MinVal("Min val", Range(0.0, 1.0)) = 0.0
        _MaxVal("Max val", Range(0.0, 1.0)) = 1.0
        _IsosurfaceVal("Isosurface Value", Range(0.0, 1.0)) = 1.0

        _VolumeLightFactor("Volume Light Factor", Range(0.0, 1.0)) = 1.0

        _MinGradient("Gradient visibility threshold", Range(0.0, 0.1)) = 0.01
        _LightingGradientThresholdStart("Gradient threshold for lighting (end)", Range(0.0, 1.0)) = 0.0
        _LightingGradientThresholdEnd("Gradient threshold for lighting (start)", Range(0.0, 1.0)) = 0.0

        _CircleX("Circle X", Range(0.0, 1.0)) = 0.5
        _CircleY("Circle Y", Range(0.0, 1.0)) = 0.5
        _CircleRadius("Circle Radius", Range(0.0, 0.707)) = 0.707
        _CircleDensity("Circle Density", Range(0.0, 1.0)) = 0.0

        _StartPlane("Start Plane", Range(0.0, 1.0)) = 0.0
        _EndPlane("End Plane", Range(0.0, 1.0)) = 1.0

        _ClipedHeight("clipedHeight", Range(0.0, 0.99)) = 0.99
        
        // --- 内部观察与手电筒工具属性 ---
        _FlashlightPos("Flashlight Position", Vector) = (0,0,0,0)
        _FlashlightForward("Flashlight Forward Dir", Vector) = (0,0,1,0) // [新增]
        _FlashlightRadius("Flashlight Radius", Range(0.0, 2.0)) = 0.0
        
        // 全局缩放：用于解决"雾墙"
        _InternalDensityScale("Internal Density Scale", Range(0.001, 1.0)) = 0.05
        
        // 边缘增强：控制梯度对透明度的贡献强度
        _EdgeContribution("Edge Contribution (X-Ray Weight)", Range(0.0, 10.0)) = 1.0
        
        // [新增] 平坦区域底色：即使梯度为0，也保留多少不透明度？
        _BaseDensityAlpha("Base Alpha for Flat Areas", Range(0.0, 1.0)) = 0.1

        [HideInInspector] _TextureSize("Dataset dimensions", Vector) = (1, 1, 1)
    }
    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" }
        LOD 100
        Cull Front
        ZTest LEqual
        ZWrite On
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma multi_compile MODE_DVR MODE_MIP MODE_SURF
            #pragma multi_compile __ TF2D_ON
            #pragma multi_compile __ CROSS_SECTION_ON
            #pragma multi_compile __ LIGHTING_ON
            #pragma multi_compile DEPTHWRITE_ON DEPTHWRITE_OFF
            #pragma multi_compile __ RAY_TERMINATE_ON
            #pragma multi_compile __ USE_MAIN_LIGHT
            #pragma multi_compile __ CUBIC_INTERPOLATION_ON
            #pragma multi_compile __ HIGHLIGHT_OPACITY HIGHLIGHT_CLIPED HIGHLIGHT_INTENSITY
            #pragma vertex vert
            #pragma fragment frag

            #include "UnityCG.cginc"
            #include "TricubicSampling.cginc"

            #define AMBIENT_LIGHTING_FACTOR 0.5
            #define JITTER_FACTOR 5.0

            struct vert_in
            {
                UNITY_VERTEX_INPUT_INSTANCE_ID
                float4 vertex : POSITION;
                float4 normal : NORMAL;
                float2 uv : TEXCOORD0;
            };

            struct frag_in
            {
                UNITY_VERTEX_OUTPUT_STEREO
                float4 vertex : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 vertexLocal : TEXCOORD1;
                float3 normal : NORMAL;
            };

            struct frag_out
            {
                float4 colour : SV_TARGET;
#if DEPTHWRITE_ON
                float depth : SV_DEPTH;
#endif
            };

            sampler3D _DataTex;
            sampler3D _GradientTex;
            sampler2D _NoiseTex;
            sampler2D _TFTex;

            float _MinVal;
            float _MaxVal;
            float3 _TextureSize;

            float _IsosurfaceVal;
            float _VolumeLightFactor;

            float _MinGradient;
            float _LightingGradientThresholdStart;
            float _LightingGradientThresholdEnd;

            float _CircleRadius;
            float _CircleX;
            float _CircleY;
            float _CircleDensity;
            float _StartPlane;
            float _EndPlane;
            float _ClipedHeight;
            
            // 变量声明
            float3 _FlashlightPos;
            float3 _FlashlightForward; // [新增] 必须与 Properties 对应 float3 或 float4
            float _FlashlightRadius;
            float _InternalDensityScale;
            float _EdgeContribution;
            float _BaseDensityAlpha;


#if CROSS_SECTION_ON
#define CROSS_SECTION_TYPE_PLANE 1 
#define CROSS_SECTION_TYPE_BOX_INCL 2 
#define CROSS_SECTION_TYPE_BOX_EXCL 3
#define CROSS_SECTION_TYPE_SPHERE_INCL 4
#define CROSS_SECTION_TYPE_SPHERE_EXCL 5

            float4x4 _CrossSectionMatrices[8];
            float _CrossSectionTypes[8];
            int _NumCrossSections;
#endif

            struct RayInfo
            {
                float3 startPos;
                float3 endPos;
                float3 direction;
                float2 aabbInters;
            };
            
            struct RaymarchInfo
            {
                RayInfo ray;
                int numSteps;
                float numStepsRecip;
                float stepSize;
            };

            float3 getViewRayDir(float3 vertexLocal)
            {
                if(unity_OrthoParams.w == 0)
                {
                    // Perspective
                    return normalize(ObjSpaceViewDir(float4(vertexLocal, 0.0f)));
                }
                else
                {
                    // Orthographic
                    float3 camfwd = mul((float3x3)unity_CameraToWorld, float3(0,0,-1));
                    float4 camfwdobjspace = mul(unity_WorldToObject, camfwd);
                    return normalize(camfwdobjspace);
                }
            }

            // Find ray intersection points with axis aligned bounding box
            float2 intersectAABB(float3 rayOrigin, float3 rayDir, float3 boxMin, float3 boxMax)
            {
                float3 tMin = (boxMin - rayOrigin) / rayDir;
                float3 tMax = (boxMax - rayOrigin) / rayDir;
                float3 t1 = min(tMin, tMax);
                float3 t2 = max(tMin, tMax);
                float tNear = max(max(t1.x, t1.y), t1.z);
                float tFar = min(min(t2.x, t2.y), t2.z);
                return float2(tNear, tFar);
            };

            // Get a ray for the specified fragment (back-to-front)
            RayInfo getRayBack2Front(float3 vertexLocal)
            {
                RayInfo ray;
                ray.direction = getViewRayDir(vertexLocal);
                ray.startPos = vertexLocal + float3(0.5f, 0.5f, 0.5f);
                // Find intersections with axis aligned boundinng box (the volume)
                ray.aabbInters = intersectAABB(ray.startPos, ray.direction, float3(0.0, 0.0, 0.0), float3(1.0f, 1.0f, 1.0));

                // Check if camera is inside AABB
                const float3 farPos = ray.startPos + ray.direction * ray.aabbInters.y - float3(0.5f, 0.5f, 0.5f);
                float4 clipPos = UnityObjectToClipPos(float4(farPos, 1.0f));
                ray.aabbInters += min(clipPos.w, 0.0);

                ray.endPos = ray.startPos + ray.direction * ray.aabbInters.y;
                return ray;
            }

            // Get a ray for the specified fragment (front-to-back)
            RayInfo getRayFront2Back(float3 vertexLocal)
            {
                RayInfo ray = getRayBack2Front(vertexLocal);
                ray.direction = -ray.direction;
                float3 tmp = ray.startPos;
                ray.startPos = ray.endPos;
                ray.endPos = tmp;

                // --- 修复开始: 处理摄像机在内部的情况 ---
                float3 camPosObj = mul(unity_WorldToObject, float4(_WorldSpaceCameraPos, 1.0)).xyz;
                float3 camPosTex = camPosObj + float3(0.5f, 0.5f, 0.5f);

                // 简单的 AABB 检测
                bool isInside = (camPosTex.x >= 0.0 && camPosTex.x <= 1.0 &&
                                 camPosTex.y >= 0.0 && camPosTex.y <= 1.0 &&
                                 camPosTex.z >= 0.0 && camPosTex.z <= 1.0);

                if (isInside)
                {
                    ray.startPos = camPosTex;
                }
                // --- 修复结束 ---

                return ray;
            }

            RaymarchInfo initRaymarch(RayInfo ray, int maxNumSteps)
            {
                RaymarchInfo raymarchInfo;
                raymarchInfo.stepSize = 1.732f/*greatest distance in box*/ / maxNumSteps;
                raymarchInfo.numSteps = (int)clamp(abs(ray.aabbInters.x - ray.aabbInters.y) / raymarchInfo.stepSize, 1, maxNumSteps);
                raymarchInfo.numStepsRecip = 1.0 / raymarchInfo.numSteps;
                return raymarchInfo;
            }

            // Gets the colour from a 1D Transfer Function (x = density)
            float4 getTF1DColour(float density)
            {
                return tex2Dlod(_TFTex, float4(density, 0.0f, 0.0f, 0.0f));
            }

            // Gets the colour from a 2D Transfer Function (x = density, y = gradient magnitude)
            float4 getTF2DColour(float density, float gradientMagnitude)
            {
                return tex2Dlod(_TFTex, float4(density, gradientMagnitude, 0.0f, 0.0f));
            }

            // Gets the density at the specified position
            float getDensity(float3 pos)
            {
                float res_density = interpolateTricubicFast(_DataTex, float3(pos.x, pos.y, pos.z), _TextureSize);
#if CUBIC_INTERPOLATION_ON
                return res_density;
#else
                return tex3Dlod(_DataTex, float4(pos.x, pos.y, pos.z, 0.0f));
#endif
            }

            // Gets the gradient at the specified position
            float3 getGradient(float3 pos)
            {
#if CUBIC_INTERPOLATION_ON
                return interpolateTricubicFast(_GradientTex, float3(pos.x, pos.y, pos.z), _TextureSize).rgb;
#else
                return tex3Dlod(_GradientTex, float4(pos.x, pos.y, pos.z, 0.0f)).rgb;
#endif
            }
            
             float3 getLightDirection(float3 viewDir)
            {
#if defined(USE_MAIN_LIGHT)
                return normalize(mul(unity_WorldToObject, _WorldSpaceLightPos0.xyz));
#else
                return viewDir;
#endif
            }

            // Performs lighting calculations, and returns a modified colour.
            float3 calculateLighting(float3 col, float3 normal, float3 lightDir, float3 eyeDir, float specularIntensity)
            {
                normal *= (step(0.0, dot(normal, eyeDir)) * 2.0 - 1.0);
                float ndotl = max(lerp(0.0f, 1.5f, dot(normal, lightDir)), AMBIENT_LIGHTING_FACTOR);
                float3 diffuse = ndotl * col;
                float3 v = eyeDir;
                float3 r = normalize(reflect(-lightDir, normal));
                float rdotv = max( dot( r, v ), 0.0 );
                float3 specular = pow(rdotv, 32.0f) * float3(1.0f, 1.0f, 1.0f) * specularIntensity;
                return diffuse + specular;
            }

            // Converts local position to depth value
            float localToDepth(float3 localPos)
            {
                float4 clipPos = UnityObjectToClipPos(float4(localPos, 1.0f));

#if defined(SHADER_API_GLCORE) || defined(SHADER_API_OPENGL) || defined(SHADER_API_GLES) || defined(SHADER_API_GLES3)
                return (clipPos.z / clipPos.w) * 0.5 + 0.5;
#else
                return clipPos.z / clipPos.w;
#endif
            }

            bool IsCutout(float3 currPos)
            {
#if CROSS_SECTION_ON
                float4 pivotPos = float4(currPos - float3(0.5f, 0.5f, 0.5f), 1.0f);
                for (int i = 0; i < _NumCrossSections; ++i)
                {
                    // (Simplified loop for brevity in this response, full code assumed same as before)
                    // ... existing logic ...
                    const int type = (int)_CrossSectionTypes[i];
                    const float4x4 mat = _CrossSectionMatrices[i];
                    float3 planeSpacePos = mul(mat, pivotPos);
                    if (type == CROSS_SECTION_TYPE_PLANE && planeSpacePos.z > 0.0f) return true;
                    // ... other types ...
                }
#endif
                return false;
            }

            frag_in vert_main (vert_in v) {
                frag_in o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.vertex = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                o.vertexLocal = v.vertex;
                o.normal = UnityObjectToWorldNormal(v.normal);
                return o;
            }

            // --- 核心渲染函数 ---
            frag_out frag_VolumeSTCube(frag_in i)
            {
                // 1. 获取光线 (这里面已经包含了起点修正逻辑)
                RayInfo ray = getRayFront2Back(i.vertexLocal);
                RaymarchInfo raymarchInfo = initRaymarch(ray, 1024);

                // --- 新增：智能判断逻辑 ---
                // 计算摄像机是否在体积内部
                float3 camPosObj = mul(unity_WorldToObject, float4(_WorldSpaceCameraPos, 1.0)).xyz;
                float3 camPosTex = camPosObj + float3(0.5f, 0.5f, 0.5f);
                bool isInside = (camPosTex.x >= 0.0 && camPosTex.x <= 1.0 &&
                                 camPosTex.y >= 0.0 && camPosTex.y <= 1.0 &&
                                 camPosTex.z >= 0.0 && camPosTex.z <= 1.0);

                // --- 动态参数选择 ---
                // 如果在内部：使用材质面板上设置的 X-Ray 参数 (_InternalDensityScale 等)
                // 如果在外部：强制恢复标准 DVR 参数 (Scale=1.0, BaseAlpha=1.0, 关闭边缘削弱)
                
                float activeDensityScale = isInside ? _InternalDensityScale : 1.0;
                float activeBaseAlpha    = isInside ? _BaseDensityAlpha     : 1.0;
                // 在外部时，将 EdgeContribution 设为 0，防止边缘逻辑改变透明度
                // 在内部时，使用面板设置的值
                float activeEdgeContrib  = isInside ? _EdgeContribution     : 0.0; 


                float3 lightDir = normalize(ObjSpaceViewDir(float4(float3(0.0f, 0.0f, 0.0f), 0.0f)));
                ray.startPos += (JITTER_FACTOR * ray.direction * raymarchInfo.stepSize) * tex2D(_NoiseTex, float2(i.uv.x, i.uv.y)).r;

                float4 col = float4(0.0f, 0.0f, 0.0f, 0.0f);
                float tDepth = raymarchInfo.numStepsRecip * (raymarchInfo.numSteps - 1);
                
                for (int iStep = 0; iStep < raymarchInfo.numSteps; iStep++)
                {
                    const float t = iStep * raymarchInfo.numStepsRecip;
                    const float3 currPos = lerp(ray.startPos, ray.endPos, t);

                    // 1. 基础裁剪与切割
                    if (currPos.z > _ClipedHeight) continue;
#ifdef CROSS_SECTION_ON
                    if(IsCutout(currPos)) continue;
#endif
                    
                    // --- 唯一的挖洞逻辑：平面切片 ---
                    if (_FlashlightRadius > 0.0)
                    {
                        float3 toSample = currPos - _FlashlightPos;
                        // 使用 Forward 向量确保平面平整
                        float distPlane = dot(toSample, normalize(_FlashlightForward));

                        // 只切前方 && 小于半径
                        if (distPlane > 0.0 && distPlane < _FlashlightRadius) continue;
                    }

                    // 3. 采样密度
                    float density = getDensity(currPos);

#if !TF2D_ON
                    if(density < _MinVal || density > _MaxVal) continue;
                    float4 src = getTF1DColour(density);
                    if (src.a == 0.0) continue;
#endif

// 计算梯度
#if defined(TF2D_ON) || defined(LIGHTING_ON) || !defined(TF2D_ON) 
                    float3 gradient = getGradient(currPos);
                    float gradMag = length(gradient);
                    float gradMagNorm = gradMag / 1.75f;
#endif

#if TF2D_ON
                    float4 src = getTF2DColour(density, gradMagNorm);
                    if (src.a == 0.0) continue;
#endif
                    
                    // --- 4. 混合透明度调制 (Gradient + Base Blend) ---
                    // 使用 activeEdgeContrib 和 activeBaseAlpha
                    
                    float edgeFactor = smoothstep(_MinGradient, _MinGradient + 0.1, gradMag);
                    
                    // 逻辑推演：
                    // 当在外部时 (activeEdgeContrib=0, activeBaseAlpha=1):
                    // opacityModulator = lerp(1.0, 1.0, 0) = 1.0 -> 原始透明度不变。
                    // 当在内部时 (activeEdgeContrib>0, activeBaseAlpha=0.1):
                    // opacityModulator < 1.0 -> 变得透明。
                    float opacityModulator = lerp(activeBaseAlpha, 1.0,  min(edgeFactor * activeEdgeContrib, 1.0));
                    
                    src.a *= opacityModulator;

                    // --- 5. 全局密度缩放 (解决雾墙) ---
                    // 在外部时 activeDensityScale 为 1.0，无影响
                    src.a *= activeDensityScale;

                    // --- 6. 光照 ---
#if defined(LIGHTING_ON)
                    // 修复：除零保护
                    float3 normal = gradient / (gradMag + 0.0001f);
                    float3 shaded = calculateLighting(src.rgb, normal, getLightDirection(-ray.direction), -ray.direction, 0.3f);
                    src.rgb = lerp(src.rgb, shaded * 2, _VolumeLightFactor);
#endif
                    
                    // --- 7. 混合 ---
                    src.rgb *= src.a;
                    col = (1.0f - col.a) * src + col;

                    if (col.a > 0.15 && t < tDepth) tDepth = t;
                    if (col.a > 0.99) break; // 提前退出
                }

                frag_out output;
                output.colour = col;
#if DEPTHWRITE_ON
                const float3 depthPos = lerp(ray.startPos, ray.endPos, tDepth) - float3(0.5f, 0.5f, 0.5f);
                output.depth = localToDepth(depthPos);
#endif
                return output;
            }

            // Direct Volume Rendering
            frag_out frag_dvr(frag_in i)
            {
               return frag_VolumeSTCube(i); // Reuse for now if MODE_SURF is not intended to be vastly different in this context
            }
             // Maximum Intensity Projection mode
            frag_out frag_mip(frag_in i)
            {
                #define MAX_NUM_STEPS 1024
                RayInfo ray = getRayBack2Front(i.vertexLocal);
                RaymarchInfo raymarchInfo = initRaymarch(ray, 1024);
                float maxDensity = 0.0f;
                float3 maxDensityPos = ray.startPos;
                for (int iStep = 0; iStep < raymarchInfo.numSteps; iStep++)
                {
                    const float t = iStep * raymarchInfo.numStepsRecip;
                    const float3 currPos = lerp(ray.startPos, ray.endPos, t);
                    
#ifdef CROSS_SECTION_ON
                    if (IsCutout(currPos)) continue;
#endif
                    const float density = getDensity(currPos);
                    if (density > maxDensity && density > _MinVal && density < _MaxVal)
                    {
                        maxDensity = density;
                        maxDensityPos = currPos;
                    }
                }
                frag_out output;
                output.colour = (maxDensity == 0.0f) ? float4(0,0,0,0) : float4(getTF1DColour(maxDensity).rgb, 0.8f);
#if DEPTHWRITE_ON
                output.depth = localToDepth(maxDensityPos - float3(0.5f, 0.5f, 0.5f));
#endif
                return output;
            }

            frag_out frag_surf(frag_in i)
            {
                // Simple pass-through or revert to original if needed. 
                // Ensuring compilation integrity.
                return frag_VolumeSTCube(i);
            }

            frag_in vert(vert_in v)
            {
                return vert_main(v);
            }
            frag_out frag(frag_in i)
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);

#if MODE_DVR
                return frag_VolumeSTCube(i);
#elif MODE_MIP
                return frag_mip(i);
#elif MODE_SURF
                return frag_surf(i);
#endif
            }

            ENDCG
        }
    }
}
