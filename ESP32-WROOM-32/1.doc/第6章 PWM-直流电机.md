# 第六章 直流电机

## 1. 导入

直流电机（DC Motor）是最常见的动力执行器。ESP32 需借助电机驱动芯片（H 桥）进行方向与转速控制：方向由两路“相位/方向”信号决定，转速通过 PWM（占空比）调速。本章覆盖常见驱动（L298N、L9110S、TB6612FNG）的接线方式、最小示例、可复用 `DCMotor` 封装、加减速斜坡与双轮差速示例，并强调电源与电磁干扰的工程注意事项。

## 2. 硬件设计

- 驱动器选择：
  
  - L298N：古早、耐用，压降大、发热重，适合入门与低要求场景。
  - TB6612FNG/DRV8833：效率更高，发热更低，推荐首选。
  - L9110S：简化 H 桥，小电流场景可用，无独立“使能”脚。

- 供电与地线：
  
  - 电机电源与 ESP32 逻辑电源可以分开供电，但 GND 必须共地。
  - 不要用 ESP32 的 3.3V 给电机供电；电机瞬时电流大，需独立电源。
  - 驱动板通常已带续流二极管；若用分立器件驱动，必须加续流二极管。

- 建议 PWM 频率：
  
  - 1–4 kHz 易闻啸叫；8–20 kHz 基本“超声”不可闻。常用 10–20 kHz。

- 接线示例（示意）：

```c
[L298N 单路: IN1/IN2 方向 + ENA 速度(PWM)]
ESP32 GPIO27 -> IN1
ESP32 GPIO14 -> IN2
ESP32 GPIO25 -> ENA(PWM)
+12V_MOTOR   -> L298N +12V
GND(ESP32)---+-> L298N GND   (共地)
电机A端子    -> OUT1/OUT2

[TB6612FNG 单路: AIN1/AIN2 方向 + PWMA 速度 + STBY 使能]
ESP32 GPIO27 -> AIN1
ESP32 GPIO14 -> AIN2
ESP32 GPIO25 -> PWMA(PWM)
ESP32 GPIO33 -> STBY (置高使能)
VM -> 电机电源(如 6-12V), VCC -> 3.3V 逻辑, GND 共地

[L9110S 单路: IA/IB 双向脚，无独立使能（可双PWM或单PWM）]
ESP32 GPIO27 -> IA (PWM)
ESP32 GPIO14 -> IB (PWM/方向)
VM -> 电机电源, GND 共地
```

- 安全与抗干扰：
  - 电机是强干扰源。为 ESP32 端加 100µF 电解 + 0.1µF 陶瓷去耦；电机端尽量短线，必要时加 RC 吸收/磁珠。
  - 大电流供电线与信号线分布走线，星形接地，避免与 USB 线并行靠近。
  - 初学慎用启动相关 GPIO（0/2/15）。

## 3. 软件设计

### 3.1 实验目标

- 使用方向引脚 + PWM 实现正反转与调速。
- 支持“滑行（coast）/快速刹车（brake）”两种停止方式。
- 提供 `DCMotor` 类统一封装，兼容 L298N/TB6612/L9110S。
- 演示加减速斜坡与双轮差速。

### 3.2 关键模块

- `machine.Pin`：方向控制
- `machine.PWM`：速度控制（占空比）
- `time` 或 `uasyncio`：时序、斜坡与并发控制

辅助函数（兼容不同固件的 `duty` 接口）：

```python
# 文件：pwmutil.py
def set_duty_frac(pwm, frac: float):
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else float(frac)
    try:
        pwm.duty(int(1023 * frac))      # 0..1023
    except AttributeError:
        pwm.duty_u16(int(65535 * frac)) # 0..65535
```

## 4. 快速上手

### 4.1 L298N：正反转 + 调速

```python
# 文件：main.py
from machine import Pin, PWM
from pwmutil import set_duty_frac
import time

IN1, IN2, ENA = 27, 14, 25

in1 = Pin(IN1, Pin.OUT, value=0)
in2 = Pin(IN2, Pin.OUT, value=0)
pwm = PWM(Pin(ENA), freq=20000)  # 20kHz

def set_dir(forward=True):
    in1.value(1 if forward else 0)
    in2.value(0 if forward else 1)

def set_speed(s):  # s: 0.0..1.0
    set_duty_frac(pwm, s)

def brake():
    # 快速刹车：IN1=IN2=1（H 桥短路电机两端，能量内耗）
    in1.value(1); in2.value(1); set_speed(0.0)

def coast():
    # 滑行：IN1=IN2=0（电机断开，靠惯性滑行）
    in1.value(0); in2.value(0); set_speed(0.0)

# 演示
set_dir(True)   # 正转
set_speed(0.6); time.sleep(2)
set_speed(0.2); time.sleep(1)
brake();        time.sleep(0.5)

set_dir(False)  # 反转
set_speed(0.5); time.sleep(2)
coast()
pwm.deinit()
```

### 4.2 TB6612FNG：注意 STBY 使能

```python
# 文件：main.py
from machine import Pin, PWM
from pwmutil import set_duty_frac
import time

AIN1, AIN2, PWMA, STBY = 27, 14, 25, 33

ain1 = Pin(AIN1, Pin.OUT, value=0)
ain2 = Pin(AIN2, Pin.OUT, value=0)
stby = Pin(STBY, Pin.OUT, value=1)   # 拉高使能
pwm  = PWM(Pin(PWMA), freq=20000)

def set_dir(forward=True):
    ain1.value(1 if forward else 0)
    ain2.value(0 if forward else 1)

def set_speed(s): set_duty_frac(pwm, s)

set_dir(True); set_speed(0.7); time.sleep(2)
set_dir(False); set_speed(0.4); time.sleep(2)
# 快速刹车：TB6612 也可 IN1=IN2=1
ain1.value(1); ain2.value(1); set_speed(0.0)
pwm.deinit()
```

### 4.3 L9110S：双 PWM（或单 PWM + 方向）

```python
# 文件：main.py
from machine import Pin, PWM
from pwmutil import set_duty_frac
import time

IA, IB = 27, 14
p1 = PWM(Pin(IA), freq=15000)
p2 = PWM(Pin(IB), freq=15000)

def drive(v):  # v: -1..1
    v = max(-1, min(1, v))
    a = abs(v)
    if v > 0:
        set_duty_frac(p1, a); set_duty_frac(p2, 0.0)
    elif v < 0:
        set_duty_frac(p1, 0.0); set_duty_frac(p2, a)
    else:
        # L9110 无真正“刹车”，此处为滑行
        set_duty_frac(p1, 0.0); set_duty_frac(p2, 0.0)

drive(0.6); time.sleep(2)
drive(-0.5); time.sleep(2)
drive(0.0)
p1.deinit(); p2.deinit()
```

示例：选择不同驱动器

```python
# 文件：main.py
from dcmotor import DCMotor
import time

# 1) L298N/TB6612（IN1/IN2 + EN(PWM)）
m = DCMotor(in1=27, in2=14, pwm_pin=25, mode='enable')
m.set_speed(0.7); time.sleep(2)
m.set_speed(-0.5); time.sleep(2)
m.brake(); time.sleep(0.5)
m.coast()

# 2) L9110S（双 PWM）
# m = DCMotor(in1=27, in2=14, pwm_pin=None, mode='dual_pwm')

m.close()
```

## 6. 非阻塞斜坡（uasyncio）

```python
# 文件：main.py
from dcmotor import DCMotor
import uasyncio as asyncio

async def main():
    m = DCMotor(27, 14, pwm_pin=25, mode='enable')
    await m.ramp_to_async(0.8, ms=1500)
    await asyncio.sleep(1)
    await m.ramp_to_async(-0.6, ms=1200)
    m.stop(brake=True)
    m.close()

asyncio.run(main())
```

## 7. 双轮差速演示（两电机）

```python
# 文件：drive2.py
from dcmotor import DCMotor
import time

# 左右轮各一个电机（按你的接线调整）
left  = DCMotor(27, 14, pwm_pin=25, mode='enable')
right = DCMotor(26, 33, pwm_pin=32, mode='enable')

def mix(v, w):
    """
    v: 线速度（-1..1），w: 角速度（-1..1）
    左右轮混合：L = v - w, R = v + w（并裁剪）
    """
    l = max(-1, min(1, v - w))
    r = max(-1, min(1, v + w))
    return l, r

# 简单路径：前进 -> 右转 -> 后退 -> 停车
for v, w, t in [
    (0.7, 0.0, 2.0),
    (0.5, 0.5, 1.5),
    (-0.6, 0.0, 1.5),
    (0.0, 0.0, 0.5),
]:
    l, r = mix(v, w)
    left.set_speed(l); right.set_speed(r)
    time.sleep(t)

left.stop(brake=True); right.stop(brake=True)
left.close(); right.close()
```

## 8. 常见问题与排查

- 电机不转或时转时不转：
  - 供电电流不足或线压降过大；检查电机电源额定电流与线材。
  - 未共地或 STBY/EN 未拉对电平（TB6612 需 STBY=1；L298N ENA 需使能）。
- ESP32 复位或串口断开：
  - 电机干扰/浪涌倒灌；增加电源去耦、电机端 RC 抑制、独立电源与星形接地。
- 啸叫明显：
  - 提高 PWM 频率至 15–25 kHz；或机械固定/减振。
- 方向相反：
  - 互换 IN1/IN2 或在软件中取反目标速度。
- 刹车无效：
  - L298N/TB6612 可用 IN1=IN2=1 实现快速刹车；L9110S 普遍不支持真正“短接刹车”，仅能滑行。

## 9. 小结

本章基于 H 桥原理实现了直流电机的方向与 PWM 调速，给出了 L298N/TB6612/L9110S 的接线方法与完整示例，并通过 `DCMotor` 封装统一了“正反转、调速、滑行/刹车、加减速斜坡”等能力；同时从供电、共地与抗干扰角度总结了直流电机驱动的工程要点。

---
