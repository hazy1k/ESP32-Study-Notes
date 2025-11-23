# 第八章 外部中断

## 1. 导入

外部中断用于在引脚电平变化时“立即响应”，适合按键、限位、脉冲计数（霍尔/编码器）、人机交互等场景。与轮询相比，中断能显著降低延迟与 CPU 占用。但中断回调函数必须“短小、无阻塞”，重活应转交到主循环或协程中处理。

## 2. 硬件设计

- 典型按键接法（上拉，按下为低）：

```c
ESP32 GPIO（输入，上拉） <---> 按键 <---> GND
                         |
                         +-- 内部上拉（Pin.PULL_UP）或外部 10kΩ 上拉
```

- 引脚选择：
  - 避免启动相关脚：GPIO0/GPIO2/GPIO15。
  - 推荐：4/5/16/17/18/19/21/22/23/25/26/27/32/33。
- 深度睡眠唤醒（EXT1）引脚需为 RTC IO（常见：0,2,4,12–15,25–27,32–39），接线前确认你的引脚是否支持 RTC。
- 抗干扰建议：
  - 线短、加 100nF 并联电容做 RC 消抖（仍建议软件消抖 20–50ms）。
  - 与强干扰设备分线走，必要时屏蔽或下拉/上拉增大抗干扰。

## 3. 软件设计

### 3.1 实验目标

- 掌握 `Pin.irq` 的使用（上升沿/下降沿触发）。
- 在中断中做最小处理，重活通过调度/协程处理。
- 实现消抖、单/双沿事件、脉冲计数。
- 演示深度睡眠下的外部唤醒（EXT1）。

### 3.2 关键模块

- `machine.Pin`：`irq(trigger=..., handler=...)`
- `time`: `ticks_ms()`/`ticks_diff()` 消抖计时
- `micropython.schedule`：从中断投递轻量任务到主线程
- `uasyncio.ThreadSafeFlag`：中断与协程的无锁同步
- `esp32.wake_on_ext1` + `machine.deepsleep`：外部唤醒

---

## 4. 基础示例：下降沿中断 + 软件消抖

```python
# 文件：main.py
from machine import Pin
import time

BTN_PIN = 13
DEBOUNCE_MS = 30

btn = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)  # 上拉输入：未按=1，按下=0
last_ms = 0

def on_falling(pin):
    # 极简消抖：两次事件间隔大于阈值
    global last_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ms) > DEBOUNCE_MS:
        last_ms = now
        # 中断里只做极少操作：标记/轻量打印
        print("Pressed!")

# 下降沿触发（按下）
btn.irq(trigger=Pin.IRQ_FALLING, handler=on_falling)

# 主循环可继续做别的事
while True:
    time.sleep_ms(200)
```

要点：

- 中断回调禁止阻塞、禁止长时间打印、禁止大量内存分配。
- 复杂逻辑用调度或协程承接（见下文）。

---

## 5. 双沿检测：按下/松开都响应

```python
# 文件：main.py
from machine import Pin
import time

BTN_PIN = 13
DEBOUNCE_MS = 30

btn = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)
last_ms = 0
state = 1  # 当前稳定电平（1=未按，0=按下）

def on_edge(pin):
    global last_ms, state
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ms) <= DEBOUNCE_MS:
        return
    last_ms = now

    val = pin.value()
    if val != state:
        state = val
        if val == 0:
            print("Pressed")
        else:
            print("Released")

btn.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=on_edge)

while True:
    time.sleep_ms(200)
```

说明：通过比较“稳定状态”与当前电平，避免在中断里执行额外读取循环。

---

## 6. 把“重活”交给主线程：micropython.schedule

`micropython.schedule(cb, arg)` 允许在中断中仅“投递任务”，由 VM 在安全点调用回调。

```python
# 文件：main.py
from machine import Pin
import time, micropython

BTN_PIN = 13
DEBOUNCE_MS = 30

btn = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)
last_ms = 0
pending = False  # 防止堆积

def worker(_):
    global pending
    pending = False
    # 这里做相对“重”的工作（打印/状态机/业务逻辑）
    print("Do heavy work outside ISR")

def isr(pin):
    global last_ms, pending
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ms) > DEBOUNCE_MS and not pending:
        last_ms = now
        pending = True
        micropython.schedule(worker, 0)

btn.irq(trigger=Pin.IRQ_FALLING, handler=isr)

while True:
    time.sleep_ms(100)
```

---

## 7. 与协程联动：ThreadSafeFlag（强烈推荐）

在中断里 `flag.set()`，协程里 `await flag.wait()` 即可无阻塞地接力处理。

```python
# 文件：main.py
from machine import Pin
import uasyncio as asyncio
import time

BTN_PIN = 13
DEBOUNCE_MS = 30

btn = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)
flag = asyncio.ThreadSafeFlag()
last_ms = 0

def isr(pin):
    global last_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ms) > DEBOUNCE_MS:
        last_ms = now
        flag.set()  # 唤醒协程

async def consumer():
    while True:
        await flag.wait()
        # 在协程上下文里处理业务
        print("Button event handled in asyncio")

async def main():
    btn.irq(trigger=Pin.IRQ_FALLING, handler=isr)
    await consumer()

asyncio.run(main())
```

---

## 8. 脉冲计数（霍尔/编码器）

在 ISR 中只做“自增计数”，读取时用“关中断”保障原子性。

```python
# 文件：main.py
from machine import Pin, disable_irq, enable_irq
import time

SIG_PIN = 34  # ADC/输入专用脚也可用于中断（不可输出）
pulse_in = Pin(SIG_PIN, Pin.IN)
count = 0

def isr(pin):
    global count
    count += 1  # 简单自增，ISR 要极短

pulse_in.irq(trigger=Pin.IRQ_RISING, handler=isr)

last = time.ticks_ms()
while True:
    time.sleep_ms(500)
    # 原子读取并清零
    state = disable_irq()
    c = count
    count = 0
    enable_irq(state)

    now = time.ticks_ms()
    dt = time.ticks_diff(now, last) / 1000  # 秒
    last = now
    print("pulses:", c, "freq(Hz):", c / dt if dt > 0 else 0)
```

---

## 9. 深度睡眠 + 外部唤醒（EXT1）

使用 EXT1 可由一个或多个 RTC 引脚“任意高”或“全低”唤醒。注意：仅 RTC IO 支持 EXT1，请选 0,2,4,12–15,25–27,32–39 等引脚。

```python
# 文件：main.py
import machine, esp32
from machine import Pin
import time

# 选择支持 RTC 的引脚，如 33
BTN = Pin(33, Pin.IN, Pin.PULL_UP)

# 配置 EXT1：任一引脚为高电平唤醒（若按键上拉，按下为低，可改为 ALL_LOW）
esp32.wake_on_ext1(pins=(BTN,), level=esp32.WAKEUP_ANY_HIGH)
print("Going to deep sleep, toggle the pin to wake...")

time.sleep_ms(300)
machine.deepsleep()  # 进入深度睡眠（唤醒后从 boot.py/main.py 重新开始）
```

唤醒后可在启动脚本中判断来源：

```python
# 放在 boot.py 或 main.py 开头
import machine
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print("Woke from deep sleep by EXT1")
```

---

## 10. 常见问题与排查

- 中断“抖动”频繁：
  - 增加消抖时间（20–50ms），硬件加 RC；使用上拉/下拉确保稳态。
- 回调里做了耗时操作导致系统卡顿：
  - 在 ISR 里只做标志；用 `micropython.schedule` 或协程处理。
- 事件丢失：
  - 频率太高、回调过重或主循环不及时处理；使用最小 ISR 并提高主循环/协程处理频度。
- 选错引脚：
  - 深度睡眠唤醒需要 RTC IO；普通中断大多 GPIO 可用，但部分功能脚有约束。
- 打印导致异常：
  - ISR 中大量 `print` 会引发时序问题；必要时缩短打印或转移到调度/协程。

## 11. 小结

本章系统介绍了 ESP32 外部中断的使用方式：`Pin.irq` 的边沿触发、软件消抖、通过 `micropython.schedule` 与 `uasyncio.ThreadSafeFlag` 将重活移到安全上下文处理；给出脉冲计数的原子读写方法，以及深度睡眠下使用 EXT1 的外部唤醒。把“快而轻”的工作放在中断，“慢而重”的逻辑交给主线程/协程，是写好中断驱动应用的关键。

---
