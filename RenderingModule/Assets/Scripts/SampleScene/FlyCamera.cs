using UnityEngine;

public class FlyCamera: MonoBehaviour
{
    public float mainSpeed = 20.0f;   // 常规移动速度
    public float shiftAdd = 50.0f;    // 按住 Shift 的加速
    public float maxShift = 200.0f;   // 最大速度
    public float camSens = 0.25f;     // 鼠标灵敏度
    private Vector3 lastMouse = new Vector3(255, 255, 255); // 上一帧鼠标位置

    void Update()
    {
        // 只有按住鼠标右键时才旋转视角
        if (Input.GetMouseButton(1))
        {
            lastMouse = Input.mousePosition - lastMouse;
            lastMouse = new Vector3(-lastMouse.y * camSens, lastMouse.x * camSens, 0);
            lastMouse = new Vector3(transform.eulerAngles.x + lastMouse.x, transform.eulerAngles.y + lastMouse.y, 0);
            transform.eulerAngles = lastMouse;
        }
        lastMouse = Input.mousePosition;

        // 键盘移动 (WASD)
        Vector3 p = GetBaseInput();
        if (Input.GetKey(KeyCode.LeftShift))
        {
            float totalRun = 1.0f;
            p = p * totalRun * shiftAdd;
            p.x = Mathf.Clamp(p.x, -maxShift, maxShift);
            p.y = Mathf.Clamp(p.y, -maxShift, maxShift);
            p.z = Mathf.Clamp(p.z, -maxShift, maxShift);
        }
        else
        {
            p = p * mainSpeed;
        }

        p = p * Time.deltaTime;
        Vector3 newPosition = transform.position;
        
        // 如果按住空格，直接向上飞 (可选)
        if (Input.GetKey(KeyCode.Space)){
            transform.Translate(Vector3.up * mainSpeed * Time.deltaTime);
        }

        transform.Translate(p);
    }

    private Vector3 GetBaseInput()
    {
        Vector3 p_Velocity = new Vector3();
        if (Input.GetKey(KeyCode.W)) p_Velocity += new Vector3(0, 0, 1);
        if (Input.GetKey(KeyCode.S)) p_Velocity += new Vector3(0, 0, -1);
        if (Input.GetKey(KeyCode.A)) p_Velocity += new Vector3(-1, 0, 0);
        if (Input.GetKey(KeyCode.D)) p_Velocity += new Vector3(1, 0, 0);
        return p_Velocity;
    }
}