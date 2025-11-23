# 第十章 PWM 呼吸灯

## 1. 导入

“呼吸灯”通过周期性改变 LED 的亮度实现柔和的明暗过渡。ESP32 使用 PWM（脉宽调制）改变占空比来控制亮度。相较简单的“闪烁”，呼吸灯需要平滑的亮度曲线（如正弦或伽马校正）来获得更自然的视觉效果。

## 2. 硬件设计

- 连接说明（与前文一致示例用 `GPIO15`，实际可换安全 GPIO 如 4/16/17/18/19/21/22/23/25/26/27/32/33）：

```c
LED(正极) -> 3.3V
LED(负极) -> 电阻(330~1kΩ) -> ESP32 GPIO15   // 常见“低电平点亮”不适用此例
```

- 更常见的是 LED 模块（带限流）或开发板板载 LED，通常为“高电平点亮”：

```c
ESP32 GPIO15 -> LED 模块 SIG/IN
3.3V         -> VCC
GND          -> GND
```

- RGB LED（共阴/共阳）：
  - 共阴（常见）：R/G/B 引脚“高电平更亮”，active_high=True。
  - 共阳：R/G/B 引脚“低电平更亮”，active_high=False（反相）。

建议：单色 LED PWM 频率设置 500 Hz~2 kHz，避免低频闪烁与可闻噪声；RGB 也可统一 1 kHz。

## 3. 软件设计

- 关键模块：
  - `machine.PWM`：`PWM(Pin(...), freq=..., duty/duty_u16)`。
  - `time`：阻塞式时序。
  - `uasyncio`：非阻塞呼吸灯。
- 兼容不同固件的占空比接口（`duty()` 或 `duty_u16()`）是常见坑，建议封装。

### 3.1 占空比兼容工具

```python
# 文件：pwmutil.py
def set_duty_frac(pwm, frac: float):
    """
    根据占空比分数(0.0..1.0)设置 duty，兼容 duty()/duty_u16()
    """
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else float(frac)
    try:
        pwm.duty(int(1023 * frac))      # 0..1023
    except AttributeError:
        pwm.duty_u16(int(65535 * frac)) # 0..65535
```

## 4. 快速上手：最小呼吸灯（阻塞式）

```python
# 文件：main.py
from machine import Pin, PWM
import time
from pwmutil import set_duty_frac

LED_PIN = 15

def breathe_blocking(pin=LED_PIN, freq=1000, step=0.02, dt=0.01):
    pwm = PWM(Pin(pin), freq=freq)
    try:
        while True:
            # 变亮
            x = 0.0
            while x <= 1.0:
                set_duty_frac(pwm, x)
                time.sleep(dt)
                x += step
            # 变暗
            x = 1.0
            while x >= 0.0:
                set_duty_frac(pwm, x)
                time.sleep(dt)
                x -= step
    finally:
        # 退出时关闭 PWM
        try: set_duty_frac(pwm, 0.0)
        except: pass
        pwm.deinit()

if __name__ == "__main__":
    breathe_blocking()
```

说明：

- `freq=1000` 基本无可见闪烁；如低亮度抖动明显，可提高至 2 kHz。
- `step`/`dt` 控制平滑度与周期时长（周期 ≈ 2 × (1/step) × dt）。

## 5. 观感优化：正弦/伽马校正

线性占空比与人眼感知不线性，“正弦缓入缓出”或“伽马校正”更柔和。下面演示正弦曲线。

```python
# 文件：main.py
from machine import Pin, PWM
import time, math
from pwmutil import set_duty_frac

LED_PIN = 15

def breathe_sine(pin=LED_PIN, freq=1000, period_ms=2000, steps=100):
    pwm = PWM(Pin(pin), freq=freq)
    try:
        while True:
            for i in range(steps):
                # t: 0..1
                t = i / (steps - 1)
                # 正弦缓入缓出：b = (1 - cos(pi*t)) / 2
                b = (1 - math.cos(math.pi * t)) * 0.5
                set_duty_frac(pwm, b)
                time.sleep_ms(period_ms // steps)
    finally:
        try: set_duty_frac(pwm, 0.0)
        except: pass
        pwm.deinit()

if __name__ == "__main__":
    breathe_sine()
```

可替换为伽马校正：`b = pow(t, gamma)`（gamma≈2.0），上升/下降段各自映射。

## 6. 封装：PWMLED 类（单色 LED）

- 支持 `active_high`（共阳/反相）、频率设置、线性/正弦/伽马曲线、一轮或持续呼吸、非阻塞协程。

```python
# 文件：pwmled.py
from machine import Pin, PWM
import time, math
try:
    import uasyncio as asyncio
except ImportError:
    asyncio = None

def _set_duty_frac(pwm, frac: float):
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else float(frac)
    try:
        pwm.duty(int(1023 * frac))
    except AttributeError:
        pwm.duty_u16(int(65535 * frac))

def _apply_active(frac, active_high):
    return frac if active_high else (1.0 - frac)

class PWMLED:
    def __init__(self, pin, freq=1000, active_high=True):
        self.pin = Pin(pin, Pin.OUT)
        self.pwm = PWM(self.pin, freq=freq)
        self.active_high = active_high
        self.set(0.0)

    def set(self, frac):
        _set_duty_frac(self.pwm, _apply_active(frac, self.active_high))

    def off(self):
        self.set(0.0)

    def on(self):
        self.set(1.0)

    def breathe_once(self, period_ms=2000, steps=100, curve="sine", gamma=2.0):
        for i in range(steps):
            t = i / (steps - 1)
            if curve == "sine":
                b = (1 - math.cos(math.pi * t)) * 0.5
            elif curve == "gamma":
                b = pow(t, gamma)
            else:  # 线性
                b = t
            self.set(b)
            time.sleep_ms(period_ms // steps)
        for i in range(steps):
            t = i / (steps - 1)
            if curve == "sine":
                b = (1 - math.cos(math.pi * (1 - t))) * 0.5
            elif curve == "gamma":
                b = pow(1 - t, gamma)
            else:
                b = 1 - t
            self.set(b)
            time.sleep_ms(period_ms // steps)

    async def breathe_forever_async(self, period_ms=2000, steps=100, curve="sine", gamma=2.0):
        if asyncio is None:
            raise RuntimeError("uasyncio 不可用")
        while True:
            for i in range(steps):
                t = i / (steps - 1)
                if curve == "sine":
                    b = (1 - math.cos(math.pi * t)) * 0.5
                elif curve == "gamma":
                    b = pow(t, gamma)
                else:
                    b = t
                self.set(b)
                await asyncio.sleep_ms(period_ms // steps)
            for i in range(steps):
                t = i / (steps - 1)
                if curve == "sine":
                    b = (1 - math.cos(math.pi * (1 - t))) * 0.5
                elif curve == "gamma":
                    b = pow(1 - t, gamma)
                else:
                    b = 1 - t
                self.set(b)
                await asyncio.sleep_ms(period_ms // steps)

    def close(self):
        try: self.off()
        except: pass
        self.pwm.deinit()
```

使用示例（阻塞一轮）：

```python
# 文件：main.py
from pwmled import PWMLED

led = PWMLED(pin=15, freq=1000, active_high=True)
try:
    led.breathe_once(period_ms=2000, steps=120, curve="sine")
finally:
    led.close()
```

使用示例（uasyncio 持续呼吸，非阻塞）：

```python
# 文件：main.py
from pwmled import PWMLED
import uasyncio as asyncio

async def main():
    led = PWMLED(pin=15, freq=1200, active_high=True)
    try:
        task = asyncio.create_task(led.breathe_forever_async(period_ms=1800, steps=120, curve="gamma", gamma=2.2))
        # 并行执行其他任务
        for _ in range(5):
            print("working...")
            await asyncio.sleep(1)
        task.cancel()
    finally:
        led.close()

asyncio.run(main())
```

## 7. RGB 彩色呼吸（单色/混色/循环）

- 共阴：`active_high=True`；共阳：`active_high=False`。
- 可让三通道同相/错相，形成渐变效果。

```python
# 文件：rgb_breath.py
from machine import Pin, PWM
import time, math

def set_duty_frac(pwm, frac: float):
    try:
        pwm.duty(int(1023 * frac))
    except AttributeError:
        pwm.duty_u16(int(65535 * frac))

class RGB:
    def __init__(self, r_pin, g_pin, b_pin, freq=1000, active_high=True):
        self.active_high = active_high
        self.r = PWM(Pin(r_pin), freq=freq)
        self.g = PWM(Pin(g_pin), freq=freq)
        self.b = PWM(Pin(b_pin), freq=freq)
        self.set(0,0,0)

    def _apply(self, ch, frac):
        frac = 0.0 if frac < 0 else 1.0 if frac > 1 else float(frac)
        frac = frac if self.active_high else (1.0 - frac)
        set_duty_frac(ch, frac)

    def set(self, r, g, b):
        self._apply(self.r, r)
        self._apply(self.g, g)
        self._apply(self.b, b)

    def close(self):
        for ch in (self.r, self.g, self.b):
            try: set_duty_frac(ch, 0.0)
            except: pass
            ch.deinit()

def breathe_rgb_cycle(r_pin=15, g_pin=2, b_pin=4, period_ms=3000, steps=150, active_high=True):
    rgb = RGB(r_pin, g_pin, b_pin, freq=1000, active_high=active_high)
    try:
        while True:
            for i in range(steps):
                t = i / (steps - 1)
                s = (1 - math.cos(math.pi * t)) * 0.5
                # 相位错开，形成彩色渐变
                r = s
                g = (1 - math.cos(math.pi * ((t + 1/3) % 1))) * 0.5
                b = (1 - math.cos(math.pi * ((t + 2/3) % 1))) * 0.5
                rgb.set(r, g, b)
                time.sleep_ms(period_ms // steps)
    finally:
        rgb.close()

if __name__ == "__main__":
    breathe_rgb_cycle()
```

## 8. 常见问题与排查

- LED 不亮/反向变暗：
  - 电平逻辑不符：共阳 RGB 记得 `active_high=False`（反相占空比）。
  - 引脚错误或未共地，检查接线与 GPIO 号。
- 低亮度抖动或闪烁：
  - 提高 PWM 频率至 1~2 kHz；在非常低亮度处步进太粗也会抖，可增加 steps 或使用伽马/正弦曲线。
- 多路 PWM 互相影响（频率被改）：
  - ESP32 PWM 基于 LEDC 定时器，多个通道共享计时器参数；尽量为一组灯效统一频率，避免频繁改频。
- 占空比接口报错：
  - 你的固件可能只有 `duty_u16()`；使用本文提供的 `set_duty_frac()` 兼容封装。
- 资源释放：
  - 停止前清零占空比并 `pwm.deinit()`；否则可能残留微弱亮光或占用资源。

## 9. 小结

本章基于 PWM 实现了单色与 RGB 的呼吸灯效果，提供了线性、正弦与伽马三种亮度曲线；给出了阻塞与 uasyncio 非阻塞两类实现，并通过 `PWMLED` 与 `RGB` 封装简化了占空比兼容与电平反相问题。结合合适的 PWM 频率与曲线映射，可获得平滑、自然的呼吸效果。

---
