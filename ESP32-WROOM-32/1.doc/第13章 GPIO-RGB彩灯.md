# 第十三章 RGB 彩灯

## 1. 导入

RGB 彩灯分两大类：

- 三色“普通 RGB LED/灯条”（共阴/共阳）：用 3 路 PWM 分别控制 R/G/B 占空比混色。
- 地址可编程灯（WS2812B/WS2811/SK6812 等，俗称 NeoPixel）：单线或双线（APA102/“点点”用 SPI）通信，逐颗独立控制，适合跑马、彩虹、渐变等复杂效果。

本章分别讲解两类 RGB 彩灯的接线与代码，覆盖 PWM 混色、伽马校正、HSV 转 RGB、基础动画，以及 NeoPixel 的高效帧刷、彩虹循环与协程非阻塞动画。

## 2. 硬件设计

### 2.1 普通 RGB LED（共阴/共阳）

- 共阴（常见）：RGB 引脚接 GPIO，经限流电阻到 LED，阴极接 GND；逻辑为高电平越亮，`active_high=True`。
- 共阳：共阳接 3.3V 或 5V，RGB 引脚下拉控制；逻辑为低电平越亮，`active_high=False`（占空需反相）。
- 典型接线（每色串 330~1kΩ 限流，示例 GPIO15/2/4）：

```c
共阴：
ESP32 GPIO15 --R--/330Ω/--> LED_R
ESP32 GPIO2  --G--/330Ω/--> LED_G
ESP32 GPIO4  --B--/330Ω/--> LED_B
LED 共阴脚 ----> GND

共阳（反相逻辑）：
ESP32 GPIO15 --R--/330Ω/--> LED_R
ESP32 GPIO2  --G--/330Ω/--> LED_G
ESP32 GPIO4  --B--/330Ω/--> LED_B
LED 共阳脚 ----> 3.3V
```

- 提示：3 路 PWM 最好统一频率（1–2 kHz），避免低亮度闪烁；ESP32 LEDC 有 16 通道，足够多路使用。

### 2.2 地址可编程 RGB（WS2812/SK6812/NeoPixel）

- 供电：5V 供电能力需足够，满白时每颗约 60mA（20mA×3 通道），10 颗灯条需 ≥600mA（建议留余量）。
- 数据线（DI）：通常接一个 GPIO（如 5），就近串 330Ω 电阻；在 5V 供电下，3.3V 逻辑一般可用，但长线或边缘情况建议加逻辑电平转换。
- 去耦：每段灯条 5V 与 GND 处并联大电解（如 ≥1000µF）抗涌流；并保证地线可靠。

```c
ESP32 GPIO5 ---- 330Ω ----> DIN(灯条)
ESP32 GND  ----------------> GND
外部 +5V  -----------------> 5V
（GND 与 ESP32 共地）
```

- APA102（DotStar）：采用 CLK/DATA 两线（SPI 类），高刷新更稳，线长更友好。

## 3. 软件设计

### 3.1 实验目标

- 普通 RGB：用 3 路 PWM 混色，支持 `active_high`、伽马校正、HSV 转换、呼吸/渐变动画。
- NeoPixel：使用 `neopixel` 模块控制灯条，支持彩虹循环、渐变、追逐，优化帧刷与非阻塞动画。

### 3.2 关键模块

- `machine.PWM`：三路 PWM 混色控制。
- `neopixel.NeoPixel`：驱动 WS2812/SK6812。
- `math`：正弦/伽马函数；HSV->RGB 转换。
- `uasyncio`：非阻塞动画并发。

---

## 4. 普通 RGB：PWM 混色与动画

### 4.1 占空比兼容与映射

```python
# 文件：pwmutil.py
def set_duty_frac(pwm, frac: float):
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else float(frac)
    try:
        pwm.duty(int(1023 * frac))
    except AttributeError:
        pwm.duty_u16(int(65535 * frac))

def apply_active(frac, active_high=True):
    return frac if active_high else (1.0 - frac)
```

### 4.2 封装：RGBPWM 类（支持伽马/HSV）

```python
# 文件：rgb_pwm.py
from machine import Pin, PWM
from math import pow, floor

try:
    import uasyncio as asyncio
except ImportError:
    asyncio = None

from pwmutil import set_duty_frac, apply_active

def hsv_to_rgb(h, s, v):
    """
    h: 0..360, s:0..1, v:0..1
    返回 r,g,b ∈ [0,1]
    """
    h = h % 360
    c = v * s
    x = c * (1 - abs(((h / 60.0) % 2) - 1))
    m = v - c
    if   0 <= h < 60:   r,g,b = c,x,0
    elif 60 <= h < 120: r,g,b = x,c,0
    elif 120<= h <180:  r,g,b = 0,c,x
    elif 180<= h <240:  r,g,b = 0,x,c
    elif 240<= h <300:  r,g,b = x,0,c
    else:               r,g,b = c,0,x
    return r+m, g+m, b+m

class RGBPWM:
    def __init__(self, r_pin, g_pin, b_pin, freq=1000, active_high=True, gamma=2.2):
        self.gamma = float(gamma)
        self.active_high = active_high
        self.r = PWM(Pin(r_pin), freq=freq)
        self.g = PWM(Pin(g_pin), freq=freq)
        self.b = PWM(Pin(b_pin), freq=freq)
        self.set_rgb(0,0,0)

    def _map(self, x):
        # 伽马校正
        x = 0.0 if x < 0 else 1.0 if x > 1 else float(x)
        xg = pow(x, self.gamma)
        return apply_active(xg, self.active_high)

    def set_rgb(self, r, g, b):
        set_duty_frac(self.r, self._map(r))
        set_duty_frac(self.g, self._map(g))
        set_duty_frac(self.b, self._map(b))

    def set_hsv(self, h, s, v):
        r,g,b = hsv_to_rgb(h,s,v)
        self.set_rgb(r,g,b)

    def close(self):
        for ch in (self.r, self.g, self.b):
            try: set_duty_frac(ch, apply_active(0.0, self.active_high))
            except: pass
            ch.deinit()

    def fade_to(self, r,g,b, ms=800, steps=80):
        # 阻塞式渐变
        import time
        # 读当前占空近似不可得，采用线性步进
        for i in range(steps+1):
            t = i/steps
            self.set_rgb(r*t, g*t, b*t)
            time.sleep_ms(max(1, ms//steps))

    async def rainbow_async(self, period_ms=3000, steps=180, s=1.0, v=0.4):
        if asyncio is None:
            raise RuntimeError("uasyncio 不可用")
        while True:
            for i in range(steps):
                h = (i * (360/steps)) % 360
                self.set_hsv(h, s, v)
                await asyncio.sleep_ms(max(1, period_ms//steps))
```

### 4.3 示例：纯色/渐变/彩虹

```python
# 文件：main.py
from rgb_pwm import RGBPWM
import uasyncio as asyncio
import time

# 共阴示例：active_high=True；若共阳请设 False
rgb = RGBPWM(r_pin=15, g_pin=2, b_pin=4, freq=1200, active_high=True, gamma=2.2)

async def main():
    # 纯色
    rgb.set_rgb(1, 0, 0); await asyncio.sleep(0.8)   # 红
    rgb.set_rgb(0, 1, 0); await asyncio.sleep(0.8)   # 绿
    rgb.set_rgb(0, 0, 1); await asyncio.sleep(0.8)   # 蓝
    # HSV 渐变
    task = asyncio.create_task(rgb.rainbow_async(period_ms=2000, steps=120, s=1.0, v=0.4))
    await asyncio.sleep(6)
    task.cancel()
    rgb.set_rgb(0,0,0)

try:
    asyncio.run(main())
finally:
    rgb.close()
```

---

## 5. NeoPixel（WS2812/SK6812）：多灯独立控制

### 5.1 基础用法

```python
# 文件：neopix_basic.py
from machine import Pin
from neopixel import NeoPixel
import time

PIN = 5
NLED = 8

np = NeoPixel(Pin(PIN), NLED)  # 大多为 GRB 格式
# 全部清空
for i in range(NLED):
    np[i] = (0,0,0)
np.write()

# 点亮第 0 颗为红色
np[0] = (255, 0, 0)
np.write()
time.sleep(0.5)

# 跑马灯
for i in range(NLED):
    for j in range(NLED):
        np[j] = (0,0,0)
    np[i] = (0, 80, 0)
    np.write()
    time.sleep(0.08)

# 全灭
for i in range(NLED):
    np[i] = (0,0,0)
np.write()
```

提示：

- 写入显示必须调用 `np.write()` 刷新。
- 避免在循环里频繁创建新元组和大对象，尽量复用或使用局部变量，降低 GC 压力。

### 5.2 伽马校正与亮度缩放

```python
# 文件：neopix_gamma.py
from machine import Pin
from neopixel import NeoPixel
from math import pow

PIN, NLED = 5, 16
np = NeoPixel(Pin(PIN), NLED)

GAMMA = 2.2
def scale_gamma(c, brightness=0.3):
    # c: 0..255；返回校正后的 0..255
    x = max(0.0, min(1.0, c/255.0))
    x = pow(x, GAMMA) * brightness
    return int(255 * x + 0.5)

def set_all(r,g,b):
    rr, gg, bb = scale_gamma(r), scale_gamma(g), scale_gamma(b)
    for i in range(NLED):
        np[i] = (rr, gg, bb)
    np.write()

set_all(255, 0, 0)
```

### 5.3 彩虹与追逐效果（非阻塞协程）

```python
# 文件：neopix_fx.py
from machine import Pin
from neopixel import NeoPixel
import uasyncio as asyncio
from math import fmod

PIN, NLED = 5, 24
np = NeoPixel(Pin(PIN), NLED)

def wheel(pos):
    # 0..255 -> (r,g,b)
    if pos < 85:
        return (255 - pos*3, pos*3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos*3, pos*3)
    pos -= 170
    return (pos*3, 0, 255 - pos*3)

async def rainbow_cycle(period_ms=2000, brightness=0.2):
    step = max(1, int(256 / NLED))
    shift = 0
    while True:
        for i in range(NLED):
            r,g,b = wheel((i*step + shift) & 255)
            # 简单亮度缩放
            np[i] = (int(r*brightness), int(g*brightness), int(b*brightness))
        np.write()
        shift = (shift + 4) & 255
        await asyncio.sleep_ms(max(1, period_ms // 256))

async def chase(color=(60,60,60), tail=6, dt_ms=40):
    idx = 0
    while True:
        # 衰减尾巴
        for i in range(NLED):
            r,g,b = np[i]
            np[i] = (r//2, g//2, b//2)
        # 点亮头
        np[idx] = color
        np.write()
        idx = (idx + 1) % NLED
        await asyncio.sleep_ms(dt_ms)

async def main():
    t1 = asyncio.create_task(rainbow_cycle(period_ms=1500, brightness=0.3))
    # 并发演示：实际项目中同一条灯带一次只跑一个效果即可
    await asyncio.sleep(5)
    t1.cancel()
    await chase(color=(0,80,40), tail=8, dt_ms=50)

asyncio.run(main())
```

---

## 6. 工程与性能建议

- 电源与电流：
  - NeoPixel 满白 60mA/颗，按最大功耗估算电源；实测多用 10–30mA/颗（动画非满白）。
  - 供电线粗且短，5V 端加大电解（≥1000µF）；长带建议多点供电。
- 逻辑电平：
  - 3.3V 驱动 5V NeoPixel 多数可行，边界条件下建议加 74AHCT125 等电平转换。
- 数据时序：
  - 写灯期间会屏蔽中断（固件实现有关），不要过于频繁刷新；常见 30–100 FPS 足够。
- 内存与 GC：
  - 避免在高频动画中创建大量临时对象；使用局部变量、复用缓冲。
- PWM 混色：
  - 多路 LEDC 通道共享少数计时器，尽量统一频率；低亮度闪烁可提高频率或使用伽马校正。
- 眼睛观感：
  - 使用伽马（2.0–2.4）或正弦曲线映射亮度，更自然；HSV 调色更直观。

## 7. 常见问题与排查

- 颜色错位或不亮：
  - NeoPixel 的颜色通道顺序常为 GRB 而非 RGB；确认模块说明或试错。
  - 接线方向错（DIN 与 DOUT 颠倒）；数据线无 330Ω 电阻易反射干扰。
- 闪烁/掉色：
  - 5V 供电不足或压降大；多点供电、加粗线、加大电容。
  - 刷新频率过高叠加 Wi‑Fi 中断；适当降低帧率或使用 APA102。
- 共阳/共阴逻辑反向：
  - 设置 `active_high=False` 并反相占空。
- 多路 PWM 互相影响：
  - 统一频率；避免频繁变更某一通道的 freq 影响其它通道。

## 8. 小结

本章实现了两类 RGB 彩灯控制：普通 RGB 通过三路 PWM 混色（支持伽马/HSV/彩虹/非阻塞动画），NeoPixel 通过单线数据逐颗控制（包含彩虹循环与追逐效果）。结合供电、电平与刷新策略的工程实践，RGB 彩灯可以稳定地呈现丰富的视觉效果。

---
