# 第二十一章 舵机控制

## 1. 导入

舵机（Servo Motor）是一种位置（角度）伺服驱动器，适用于需要角度不断变化并可以保持的控制系统。在机器人关节、云台控制、机械臂等场景中无处不在。本章将深入 ESP32 的 PWM 底层，从零构建高精度的舵机驱动，解决常见的“抖动”与“电源重启”问题，并实现带有速度控制的“平滑转动”。

- **控制原理**：PWM（脉宽调制）。
- **核心公式**：
  - 周期：通常为 20ms（50Hz）。
  - 高电平脉宽（thigh​）：决定角度。
  - LaTeX：`Duty_{u16} = \frac{t_{high}(\mu s)}{20000} \times 65535`

## 2. 规格与选型

- **模拟舵机（常见）**：
  - **SG90 / MG90S**：微型舵机（9g），扭矩约 1.5-2kg/cm。SG90 为尼龙齿（易崩齿），MG90S 为金属齿。适合轻量级云台、开关触发。
  - **MG996R / DS3218**：标准舵机，扭矩 10-20kg/cm，电流需求大，必须独立供电。
- **角度范围**：
  - **180° 舵机**：只能在 0~180 度之间控制绝对位置（本章重点）。
  - **360° 舵机**：PWM 信号控制的是**转速和方向**，无法定位角度（常用于轮式机器人驱动）。
- **脉宽标准**：
  - 绝大多数 SG90/MG996R 使用 **500μs ~ 2500μs** 对应 **0° ~ 180°**。
  - 少部分旧型号使用 1000μs ~ 2000μs 对应 0° ~ 90°/180°。

## 3. 硬件连接

- **引脚定义**：
  
  - **棕/黑**：GND（地线）。
  - **红**：VCC（电源正极，通常 4.8V - 6V）。
  - **橙/黄/白**：Signal（信号线，接 ESP32 GPIO）。

- **电源陷阱（重中之重）**：
  
  - **禁止**将舵机 VCC 接在 ESP32 开发板的 3.3V 引脚。
  - **慎用**开发板的 5V（VIN）引脚驱动大扭矩舵机（MG996R 等），启动瞬间电流（>1A）可能拉低电压导致 ESP32 重启（Brownout）。
  - **推荐方案**：使用独立 5V 电源（或锂电池降压），并务必将电源 GND 与 ESP32 GND **共地**。

- **接线示例**：

```c
[独立电源 5V] (+) -----> [舵机 红线]
[独立电源 GND] (-) --+--> [舵机 棕线]
                    |
[ESP32 GND] --------+    (必须共地！)
[ESP32 GPIO] ----------> [舵机 橙/黄线]
```

## 4. 核心工具：数学映射与分辨率

ESP32 的 `machine.PWM` 拥有 16 位分辨率（0-65535），远高于 Arduino 的默认 8 位（0-255）。这意味着我们可以实现极高精度的控制，消除舵机动作时的“颗粒感”。

```python
# 文件：servo_utils.py
def map_value(x, in_min, in_max, out_min, out_max):
    """
    线性映射函数：将角度映射到脉宽，或将脉宽映射到占空比
    """
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def calculate_duty(angle, angle_max=180, min_us=500, max_us=2500, freq=50):
    """
    计算指定角度对应的 ESP32 duty_u16 数值
    """
    # 1. 角度限幅
    angle = max(0, min(angle_max, angle))

    # 2. 角度 -> 脉宽 (us)
    pulse_us = map_value(angle, 0, angle_max, min_us, max_us)

    # 3. 脉宽 -> 占空比 (0-65535)
    # 周期 us = 1,000,000 / freq
    period_us = 1000000 / freq
    duty = int((pulse_us / period_us) * 65535)
    return duty
```

## 5. 驱动一：基础舵机类（BaseServo）

这是一个轻量级驱动，用于快速测试和简单控制。

```python
# 文件：servo.py
from machine import Pin, PWM
from servo_utils import calculate_duty
import time

class Servo:
    def __init__(self, pin, freq=50, min_us=500, max_us=2500, max_angle=180):
        """
        pin: GPIO 引脚号
        min_us/max_us: 0度和180度对应的脉宽，SG90通常是500-2500
        """
        self.pwm = PWM(Pin(pin), freq=freq)
        self.min_us = min_us
        self.max_us = max_us
        self.max_angle = max_angle
        self.freq = freq
        self.current_angle = 0
        self.write(0) # 初始归位

    def write(self, angle):
        """
        绝对角度控制（瞬动）
        """
        duty = calculate_duty(angle, self.max_angle, self.min_us, self.max_us, self.freq)
        self.pwm.duty_u16(duty)
        self.current_angle = angle

    def deinit(self):
        """
        释放 PWM 资源，停止信号输出（舵机不再锁力，可手掰动）
        """
        self.pwm.deinit()
```

## 6. 驱动二：平滑舵机类（SmoothServo）

直接使用 `write(angle)` 会导致舵机全速转动，产生冲击和电流尖峰。工业级控制通常需要“速度控制”。本类通过时间分片实现平滑的缓动效果。

```python
# 文件：smooth_servo.py
from servo import Servo
import time
import math

class SmoothServo(Servo):
    def move(self, target_angle, speed_ms_per_deg=10):
        """
        阻塞式平滑移动
        target_angle: 目标角度
        speed_ms_per_deg: 转动 1 度需要多少毫秒（越大越慢）
        """
        target_angle = max(0, min(self.max_angle, target_angle))
        start_angle = self.current_angle

        # 计算步长方向
        step = 1 if target_angle > start_angle else -1

        # 如果已经到达，直接返回
        if start_angle == target_angle:
            return

        # 循环步进
        for angle in range(int(start_angle), int(target_angle) + step, step):
            self.write(angle)
            time.sleep_ms(speed_ms_per_deg)

    def move_ease(self, target_angle, duration_ms=1000):
        """
        [进阶] 使用非线性插值（缓入缓出）移动 - 模拟机械臂质感
        duration_ms: 整个动作耗时
        """
        steps = 50 # 分50步完成
        dt = duration_ms / steps
        start = self.current_angle
        diff = target_angle - start

        for i in range(steps + 1):
            # S形曲线公式 (Sigmoid-like easing)
            t = i / steps
            # Ease-in-out cubic
            ease = t * t * (3 - 2 * t) 

            new_angle = start + diff * ease
            self.write(new_angle)
            time.sleep_ms(int(dt))
```

## 7. 实战一：基础扫角测试

验证舵机好坏，确定物理死区。

```python
# 文件：test_sweep.py
from smooth_servo import SmoothServo
import time

# GPIO 21 接舵机
# 注意：如果 0度 或 180度 发出滋滋声，说明物理受限，需调整 min_us 或 max_us
my_servo = SmoothServo(pin=21, min_us=500, max_us=2500)

try:
    while True:
        print("To 180...")
        # 慢速去 180 度
        my_servo.move(180, speed_ms_per_deg=15)
        time.sleep(0.5)

        print("To 0...")
        # 快速回 0 度
        my_servo.move(0, speed_ms_per_deg=5)
        time.sleep(0.5)

        print("Easing Mode...")
        # 带有“阻尼感”的缓入缓出
        my_servo.move_ease(180, duration_ms=1500)
        time.sleep(0.5)
        my_servo.move_ease(0, duration_ms=1500)
        time.sleep(1)

except KeyboardInterrupt:
    my_servo.deinit()
    print("Stopped")
```

## 8. 实战二：电位器旋钮控制（模拟机械臂示教）

使用 ADC 读取电位器电压，实时控制舵机角度。加入了 `IIR` 滤波防止舵机因 ADC 噪点而抖动。

```python
# 文件：knob_control.py
from machine import Pin, ADC
from servo import Servo
import time

# 硬件准备：
# 舵机 -> GPIO 21
# 电位器 -> GPIO 34 (仅限输入引脚)

adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB) # 0-3.3V 量程
servo = Servo(pin=21)

# 简单的一阶低通滤波，防止 ADC 跳变导致舵机抖动
last_val = 0
alpha = 0.1 

try:
    while True:
        raw = adc.read() # 0-4095

        # 滤波处理
        current_val = last_val + alpha * (raw - last_val)
        last_val = current_val

        # 映射：4095 -> 180度
        angle = int((current_val / 4095) * 180)

        # 只有变化超过 1 度才写入，减少舵机电流消耗
        if abs(angle - servo.current_angle) > 1:
            servo.write(angle)

        time.sleep_ms(20) # 50Hz 刷新率

except KeyboardInterrupt:
    servo.deinit()
```

## 9. 常见问题与排查

- **舵机疯狂抖动（Jitter）**：
  
  - **电源不稳**：这是 90% 的原因。特别是 ESP32 WiFi 启动时，3.3V 纹波大。请换用独立 5V 供电。
  - **ADC 噪声**：如果是旋钮控制，ADC 输入波动会导致舵机来回修正。需加软件滤波（如上例）。
  - **信号线过长**：PWM 线超过 30cm 可能受干扰，可尝试串联 100Ω 电阻。

- **上电瞬间舵机乱转**：
  
  - ESP32 上电时某些引脚会输出调试信息（波形），导致舵机误动作。
  - **避坑**：避免使用 GPIO 1, 3 (UART0), GPIO 12 (MTDI), GPIO 0, 2 (Boot strap)。**推荐使用 GPIO 4, 5, 16, 17, 21, 22**。

- **舵机发出“滋滋”堵转声**：
  
  - 说明目标角度超过了机械限位。立刻断电！
  - **解决**：软件上将范围限制在 `10° ~ 170°`，或者微调 `min_us` (比如设为 600) 和 `max_us` (设为 2400)。

- **ESP32 反复重启**：
  
  - 典型的 Brownout（电压骤降）。舵机启动电流太大，拉低了系统电压。请加强电源供电能力。

## 10. 小结

本章实现了从底层 PWM 到高级平滑算法的舵机控制体系。对于简单的应用，使用 `Servo` 类即可；对于追求动作质感的机器人项目，请务必使用 `SmoothServo` 并配合缓入缓出算法。实战中， **“电源独立”** 和 **“共地”** 是系统稳定的基石，而**软件滤波**和**速度控制**则是提升系统“高级感”的关键。

---
