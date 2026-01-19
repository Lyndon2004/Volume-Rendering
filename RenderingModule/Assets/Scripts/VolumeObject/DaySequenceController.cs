using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

namespace UnityVolumeRendering
{
    /// <summary>
    /// 简单的时间序列控制器
    /// 通过激活/隐藏子物体来切换不同天的数据
    /// </summary>
    public class DaySequenceController : MonoBehaviour
    {
        [Header("播放设置")]
        [Tooltip("每天显示的时间（秒）")]
        public float secondsPerDay = 1.0f;
        
        [Tooltip("是否自动播放")]
        public bool autoPlay = false;
        
        [Tooltip("是否循环")]
        public bool loop = true;

        [Header("日期设置")]
        [Tooltip("起始日期 (格式: 2024-01-01)")]
        public string startDate = "2024-01-01";

        [Header("当前状态")]
        [SerializeField]
        private int currentDayIndex = 0;
        
        [SerializeField]
        private int totalDays = 0;
        
        [SerializeField]
        private bool isPlaying = false;

        // 所有天的 GameObject 列表
        private List<GameObject> dayObjects = new List<GameObject>();
        
        // 计时器
        private float timer = 0f;
        
        // 起始日期
        private System.DateTime startDateTime;

        // 事件
        public UnityEvent<int, string> onDayChanged;

        void Start()
        {
            // 解析起始日期
            if (!System.DateTime.TryParse(startDate, out startDateTime))
            {
                startDateTime = System.DateTime.Now;
            }
            
            // 收集所有子物体
            CollectDayObjects();
            
            // 初始化显示第一天
            ShowDay(0);
            
            // 自动播放
            if (autoPlay)
            {
                Play();
            }
        }

        void Update()
        {
            // 键盘控制
            HandleInput();
            
            // 自动播放
            if (isPlaying)
            {
                timer += Time.deltaTime;
                if (timer >= secondsPerDay)
                {
                    timer = 0f;
                    NextDay();
                }
            }
        }

        void HandleInput()
        {
            // 空格键：播放/暂停
            if (Input.GetKeyDown(KeyCode.Space))
            {
                TogglePlay();
            }
            
            // 左右箭头：前后切换
            if (Input.GetKeyDown(KeyCode.LeftArrow))
            {
                PreviousDay();
            }
            if (Input.GetKeyDown(KeyCode.RightArrow))
            {
                NextDay();
            }
            
            // 数字键 1-9：快速跳转
            for (int i = 0; i < 9; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                {
                    int targetDay = i * (totalDays / 9);
                    GoToDay(targetDay);
                }
            }
        }

        /// <summary>
        /// 收集所有子物体
        /// </summary>
        void CollectDayObjects()
        {
            dayObjects.Clear();
            
            for (int i = 0; i < transform.childCount; i++)
            {
                dayObjects.Add(transform.GetChild(i).gameObject);
            }
            
            totalDays = dayObjects.Count;
            Debug.Log($"[DaySequence] 找到 {totalDays} 天的数据");
        }

        /// <summary>
        /// 显示指定天，隐藏其他
        /// </summary>
        public void ShowDay(int dayIndex)
        {
            if (dayIndex < 0 || dayIndex >= totalDays)
            {
                Debug.LogWarning($"日期索引超出范围: {dayIndex}");
                return;
            }
            
            // 隐藏所有
            for (int i = 0; i < dayObjects.Count; i++)
            {
                dayObjects[i].SetActive(i == dayIndex);
            }
            
            currentDayIndex = dayIndex;
            
            // 触发事件
            string dateStr = GetDateString(dayIndex);
            onDayChanged?.Invoke(dayIndex, dateStr);
            
            Debug.Log($"[DaySequence] 显示第 {dayIndex + 1}/{totalDays} 天: {dateStr}");
        }

        /// <summary>
        /// 跳转到指定天
        /// </summary>
        public void GoToDay(int dayIndex)
        {
            ShowDay(dayIndex);
            timer = 0f;
        }

        /// <summary>
        /// 下一天
        /// </summary>
        public void NextDay()
        {
            int next = currentDayIndex + 1;
            if (next >= totalDays)
            {
                if (loop)
                    next = 0;
                else
                {
                    Pause();
                    return;
                }
            }
            ShowDay(next);
        }

        /// <summary>
        /// 上一天
        /// </summary>
        public void PreviousDay()
        {
            int prev = currentDayIndex - 1;
            if (prev < 0)
            {
                if (loop)
                    prev = totalDays - 1;
                else
                    return;
            }
            ShowDay(prev);
        }

        /// <summary>
        /// 播放
        /// </summary>
        public void Play()
        {
            isPlaying = true;
            timer = 0f;
        }

        /// <summary>
        /// 暂停
        /// </summary>
        public void Pause()
        {
            isPlaying = false;
        }

        /// <summary>
        /// 切换播放/暂停
        /// </summary>
        public void TogglePlay()
        {
            if (isPlaying)
                Pause();
            else
                Play();
        }

        /// <summary>
        /// 停止并回到第一天
        /// </summary>
        public void Stop()
        {
            Pause();
            GoToDay(0);
        }

        /// <summary>
        /// 获取日期字符串
        /// </summary>
        public string GetDateString(int dayIndex)
        {
            return startDateTime.AddDays(dayIndex).ToString("yyyy-MM-dd");
        }

        /// <summary>
        /// 获取当前日期字符串
        /// </summary>
        public string GetCurrentDateString()
        {
            return GetDateString(currentDayIndex);
        }

        /// <summary>
        /// 获取当前天索引
        /// </summary>
        public int GetCurrentDayIndex() => currentDayIndex;

        /// <summary>
        /// 获取总天数
        /// </summary>
        public int GetTotalDays() => totalDays;

        /// <summary>
        /// 是否正在播放
        /// </summary>
        public bool IsPlaying() => isPlaying;

        /// <summary>
        /// 设置播放速度
        /// </summary>
        public void SetSpeed(float secondsPerDay)
        {
            this.secondsPerDay = Mathf.Max(0.1f, secondsPerDay);
        }

        /// <summary>
        /// 通过滑块设置当前天 (0-1)
        /// </summary>
        public void SetDayBySlider(float normalized)
        {
            int dayIndex = Mathf.RoundToInt(normalized * (totalDays - 1));
            GoToDay(dayIndex);
        }

        /// <summary>
        /// 获取归一化进度 (0-1)
        /// </summary>
        public float GetNormalizedProgress()
        {
            if (totalDays <= 1) return 0f;
            return (float)currentDayIndex / (totalDays - 1);
        }
    }
}
