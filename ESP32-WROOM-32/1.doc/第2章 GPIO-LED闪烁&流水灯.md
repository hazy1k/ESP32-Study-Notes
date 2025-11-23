# 第二章 LED 进阶：闪烁与流水灯

## 1. 导入

本章在“点亮一个 LED”的基础上，系统实现 LED 闪烁与流水灯两类效果，并介绍三种常见时序方案：阻塞循环、硬件定时器与 uasyncio 协程。我们还将封装可复用的 LED/LEDArray 类，便于后续扩展更多灯效。

## 2. 硬件设计

- 硬件资源：
  - LED 模块（D1–D8）
  - ESP32 开发板 GPIO
- 接线说明（与第一章一致，可只接前几路用于演示）：

```c
LED 模块 --> ESP32 IO
(D1-D8)  --> (15, 2, 0, 4, 16, 17, 5, 18)
GND      --> GND
VCC      --> 3.3V（若 LED 模块需供电）
```

- 注意：
  - GPIO0/GPIO2/GPIO15 参与启动模式；若遇到上电异常，可将这些脚替换为 4/16/17/18/19/21/22/23/25/26/27/32/33 等安全 GPIO。
  - 若为“低电平点亮”模块，逻辑需反转。

## 3. 软件设计

### 3.1 实验目标

- 让一个或多个 LED 按指定节奏闪烁。
- 实现“流水灯”（逐个点亮/熄灭）、“往返扫描”等模式。
- 学会阻塞、定时器与协程三种实现方式。

### 3.2 关键模块

- `machine.Pin`：GPIO 控制
- `time`：简单延时
- `machine.Timer`：周期性回调（非阻塞主循环）
- `uasyncio`：协程并发（多任务节奏互不影响）

---

## 4. LED 闪烁

### 4.1 阻塞式闪烁（最易上手）

```python
# 文件：main.py
from machine import Pin
import time

def main():
    led = Pin(15, Pin.OUT)
    while True:
        led.value(1)   # 高电平点亮
        time.sleep(0.5)
        led.value(0)   # 低电平熄灭
        time.sleep(0.5)

if __name__ == "__main__":
    main()
```

要点：简单直观，但主循环被“睡眠”阻塞，无法并行做其他事情。

### 4.2 定时器闪烁（非阻塞）

```python
# 文件：main.py
from machine import Pin, Timer
import time

led = Pin(15, Pin.OUT)
tim = Timer(0)

def _toggle(_):
    led.value(1 - led.value())

def main():
    tim.init(period=250, mode=Timer.PERIODIC, callback=_toggle)  # 4Hz 闪烁
    # 主循环可继续做其他工作
    while True:
        # 这里可以轮询传感器/打印日志等
        time.sleep(1)

if __name__ == "__main__":
    main()
```

要点：回调在中断上下文执行，避免在回调中分配大内存或做耗时操作。

### 4.3 uasyncio 多任务闪烁（并发、多节奏）

```python
# 文件：main.py
from machine import Pin
import uasyncio as asyncio

pins = [15, 2, 0]  # 按需裁剪
leds = [Pin(p, Pin.OUT) for p in pins]

async def blink(pin_obj, period):
    while True:
        pin_obj.value(1 - pin_obj.value())
        await asyncio.sleep(period)

async def main():
    tasks = [asyncio.create_task(blink(leds[i], 0.2 + 0.2*i)) for i in range(len(leds))]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

要点：每个 LED 一个协程，互不影响，便于扩展更多逻辑。

---

## 5. 封装：LED 与 LEDArray

### 5.1 `LED` 类（兼容高/低电平点亮）

```python
# 文件：led.py
from machine import Pin

class LED:
    def __init__(self, pin, active_high=True, init_on=False):
        self.pin = Pin(pin, Pin.OUT)
        self.active_high = active_high
        self.off()
        if init_on:
            self.on()

    def on(self):
        self.pin.value(1 if self.active_high else 0)

    def off(self):
        self.pin.value(0 if self.active_high else 1)

    def is_on(self):
        return self.pin.value() == (1 if self.active_high else 0)

    def toggle(self):
        if self.is_on():
            self.off()
        else:
            self.on()
```

### 5.2 `LEDArray` 类（流水/往返/交替/随机）

```python
# 文件：led_array.py
from machine import Pin
import time
try:
    import urandom as random  # MicroPython
except ImportError:
    import random

class LEDArray:
    def __init__(self, pins, active_high=True):
        self.active_high = active_high
        self.leds = [Pin(p, Pin.OUT) for p in pins]
        self.all_off()

    def _write(self, idx, on):
        v = 1 if (on == self.active_high) else 0
        self.leds[idx].value(v)

    def all_on(self):
        for i in range(len(self.leds)):
            self._write(i, True)

    def all_off(self):
        for i in range(len(self.leds)):
            self._write(i, False)

    def set_one(self, idx):
        self.all_off()
        self._write(idx, True)

    # 流水灯：从左到右逐个点亮
    def chase(self, delay=0.08, loops=1):
        for _ in range(loops):
            for i in range(len(self.leds)):
                self.set_one(i)
                time.sleep(delay)
        self.all_off()

    # 往返扫描（KITT/骑士灯）
    def bounce(self, delay=0.06, loops=1):
        n = len(self.leds)
        for _ in range(loops):
            for i in range(n):
                self.set_one(i); time.sleep(delay)
            for i in range(n-2, 0, -1):
                self.set_one(i); time.sleep(delay)
        self.all_off()

    # 交替闪烁（偶数与奇数分组）
    def alternate(self, delay=0.2, loops=5):
        even = [i for i in range(len(self.leds)) if i % 2 == 0]
        odd  = [i for i in range(len(self.leds)) if i % 2 == 1]
        for _ in range(loops):
            self.all_off()
            for i in even: self._write(i, True)
            time.sleep(delay)
            self.all_off()
            for i in odd:  self._write(i, True)
            time.sleep(delay)
        self.all_off()

    # 随机闪烁（星星点点）
    def sparkle(self, delay=0.05, duration=3.0):
        t = 0.0
        while t < duration:
            idx = random.randrange(0, len(self.leds))
            self._write(idx, True)
            time.sleep(delay)
            self._write(idx, False)
            t += delay
        self.all_off()
```

### 5.3 模式演示入口

```python
# 文件：main.py
from led_array import LEDArray

# 如担心启动脚，可改为 [4, 16, 17, 5, 18, 19, 21, 22]
PINS = [15, 2, 0, 4, 16, 17, 5, 18]
ACTIVE_HIGH = True  # 若为低电平点亮，改为 False
MODE = "bounce"     # 可选：chase | bounce | alternate | sparkle

def main():
    arr = LEDArray(PINS, active_high=ACTIVE_HIGH)
    if MODE == "chase":
        arr.chase(delay=0.08, loops=6)
    elif MODE == "bounce":
        arr.bounce(delay=0.06, loops=8)
    elif MODE == "alternate":
        arr.alternate(delay=0.2, loops=10)
    elif MODE == "sparkle":
        arr.sparkle(delay=0.03, duration=5.0)
    else:
        print("Unknown MODE:", MODE)
        arr.all_off()

if __name__ == "__main__":
    main()
```

---

## 6. 进阶：非阻塞流水（uasyncio 版本）

适合在不阻塞主流程的前提下，持续播放灯效或并发运行多种任务。

```python
# 文件：main.py
from machine import Pin
import uasyncio as asyncio

PINS = [15, 2, 0, 4, 16, 17, 5, 18]
ACTIVE_HIGH = True

def set_pin(pin, on):
    pin.value(1 if (on == ACTIVE_HIGH) else 0)

async def chase_async(pins, delay=0.08):
    n = len(pins)
    idx = 0
    while True:
        for i in range(n):
            set_pin(pins[i], i == idx)
        idx = (idx + 1) % n
        await asyncio.sleep(delay)

async def bounce_async(pins, delay=0.06):
    n = len(pins)
    idx, step = 0, 1
    while True:
        for i in range(n):
            set_pin(pins[i], i == idx)
        idx += step
        if idx == n - 1 or idx == 0:
            step = -step
        await asyncio.sleep(delay)

async def main():
    pin_objs = [Pin(p, Pin.OUT) for p in PINS]
    # 并发两个模式，演示多任务（实际运行时二选一更直观）
    t1 = asyncio.create_task(chase_async(pin_objs, delay=0.08))
    t2 = asyncio.create_task(bounce_async(pin_objs, delay=0.12))
    await asyncio.sleep(6)  # 播放一段时间
    for t in (t1, t2):
        t.cancel()

asyncio.run(main())
```

---

## 7. 性能与稳定建议

- 预先创建 `Pin` 对象并复用，减少循环内开销。
- 定时器回调保持短小；复杂逻辑放到主循环或协程。
- 若灯效频繁切换，注意释放/取消协程与定时器，避免资源泄漏。
- 不同固件版本的 PWM 接口略有差异（本章未用到 PWM）；若使用呼吸灯，可用 `duty()` 或 `duty_u16()` 适配。

## 8. 常见问题与排查

- 流水顺序错乱：
  - 确认引脚顺序与物理接线一致；必要时调整 `PINS` 列表顺序。
- 速度不符合预期：
  - `delay` 太小会受调度与执行开销影响；适当增大或简化回调逻辑。
- 多模式并发出现闪烁冲突：
  - 同一组引脚被多个任务同时控制会“抢灯”；确保同一时间仅一个任务写同一引脚。
- 上电异常或烧录失败：
  - 避免强占用启动脚；拔掉 LED 模块后再试；确认线缆与串口占用情况。

## 9. 小结

本章从三种时序方法（阻塞、定时器、uasyncio）出发，实现了单灯闪烁与多灯流水/往返/交替/随机等效果，并通过 `LED` 与 `LEDArray` 封装提升了可复用性与可维护性。在此基础上，你可以方便地组合出更复杂的灯效与交互逻辑。

---
