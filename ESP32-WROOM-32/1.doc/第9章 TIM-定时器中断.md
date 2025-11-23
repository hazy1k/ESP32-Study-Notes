# 第九章 定时器中断

## 1. 导入

定时器中断用于以固定时间间隔触发回调，常用于周期性采样、LED 闪烁、软件定时任务、心跳与看门狗等。相较于轮询，定时器中断延迟更低、占用更少；但回调运行在中断上下文（ISR），必须“短小、无阻塞、少分配”。本章系统介绍 ESP32 上 MicroPython 的 `machine.Timer` 用法、避坑点、与 `uasyncio`/`micropython.schedule` 的安全联动，以及可复用的周期任务封装。

## 2. 基本概念与限制

- 定时器类型：
  - 硬件定时器：`Timer(0..3)`（ESP32 一般有 4 个），抖动小、精准度高。
  - 软件定时器：`Timer(-1)`（虚拟定时器，使用系统节拍），占用少、精度略低。
- 模式：
  - `Timer.ONE_SHOT`：单次触发。
  - `Timer.PERIODIC`：周期触发。
- 回调限制（ISR 约束）：
  - 不要阻塞（禁用 `sleep`/`uasyncio` 等）。
  - 避免大量内存分配与复杂逻辑，尽量只“设标志/累加计数”。
  - 如需做“重活”，使用 `micropython.schedule` 或 `uasyncio.ThreadSafeFlag` 把工作交给主循环/协程。
- 生命周期：
  - 初始化后回调即开始触发；`deinit()` 必须及时释放。
  - 修改周期需调用 `tim.init(...)` 重新配置。

提示：在 `boot.py` 中调用一次 `micropython.alloc_emergency_exception_buf(100)` 可让中断异常具备紧急缓冲打印，有助调试。

```python
# 文件：boot.py
import micropython
micropython.alloc_emergency_exception_buf(100)
```

## 3. 快速上手

### 3.1 单次定时（ONE_SHOT）

```python
# 文件：main.py
from machine import Timer
import time

tim = Timer(0)
fired = False

def onetime_cb(t):
    global fired
    fired = True  # ISR 中只做标志

def main():
    tim.init(period=500, mode=Timer.ONE_SHOT, callback=onetime_cb)  # 500ms 后触发一次
    t0 = time.ticks_ms()
    while not fired:
        time.sleep_ms(10)
    print("ONE_SHOT fired at", time.ticks_diff(time.ticks_ms(), t0), "ms")
    tim.deinit()

if __name__ == "__main__":
    main()
```

### 3.2 周期定时（PERIODIC）闪烁 LED

```python
# 文件：main.py
from machine import Pin, Timer
import time

led = Pin(15, Pin.OUT, value=0)
tim = Timer(1)

def toggle_cb(t):
    led.value(1 - led.value())  # ISR 中操作引脚是可行的，但要短小

def main():
    tim.init(period=500, mode=Timer.PERIODIC, callback=toggle_cb)  # 2Hz
    try:
        while True:
            time.sleep_ms(1000)   # 主循环可做别的事
    finally:
        tim.deinit()
        led.value(0)

if __name__ == "__main__":
    main()
```

## 4. 将“重活”移出中断

### 4.1 micropython.schedule：从 ISR 投递到主线程

```python
# 文件：main.py
from machine import Timer
import micropython

tim = Timer(2)
pending = False

def worker(_):
    global pending
    pending = False
    # 在主线程安全执行“重活”（I/O、打印、内存分配等）
    print("Heavy work outside ISR")

def isr_cb(t):
    global pending
    if not pending:          # 防止堆积
        pending = True
        micropython.schedule(worker, 0)

tim.init(period=200, mode=Timer.PERIODIC, callback=isr_cb)

try:
    import time
    while True:
        time.sleep_ms(500)
finally:
    tim.deinit()
```

### 4.2 与 uasyncio 联动：ThreadSafeFlag

```python
# 文件：main.py
from machine import Timer
import uasyncio as asyncio

flag = asyncio.ThreadSafeFlag()
tim = Timer(3)

def isr_cb(t):
    flag.set()   # ISR 中仅设标志

async def consumer():
    while True:
        await flag.wait()
        # 在协程上下文里处理任务
        print("Tick in asyncio")

async def main():
    tim.init(period=250, mode=Timer.PERIODIC, callback=isr_cb)
    try:
        await consumer()
    finally:
        tim.deinit()

asyncio.run(main())
```

## 5. 可复用封装：安全周期任务 Ticker

- 特性：硬/软定时器可选；回调在主线程或协程里执行（非 ISR）；支持启动/停止/重置周期。
- 适合：心跳、统计上报、周期扫描等。

```python
# 文件：ticker.py
from machine import Timer
import micropython

try:
    import uasyncio as asyncio
except ImportError:
    asyncio = None

class Ticker:
    def __init__(self, period_ms=1000, timer_id=0, use_soft=False, use_async=False):
        """
        period_ms: 周期(ms)
        timer_id: 硬件定时器编号（0..3）；use_soft=True 时固定使用 -1
        use_soft: 使用软件定时器 Timer(-1)
        use_async: 使用 uasyncio 执行回调（否则用 micropython.schedule）
        """
        self.period = int(period_ms)
        self.use_async = use_async and (asyncio is not None)
        self.tim = Timer(-1 if use_soft else timer_id)
        self._cb = None
        self._pending = False

    def _sched_worker(self, _=0):
        self._pending = False
        if self._cb:
            self._cb()

    async def _async_worker(self):
        if self._cb:
            self._cb()

    def _isr(self, t):
        if self.use_async:
            # asyncio 模式下，用 ThreadSafeFlag 更合适，这里简化直接 schedule
            micropython.schedule(lambda _=0: asyncio.create_task(self._async_worker()), 0)
        else:
            if not self._pending:
                self._pending = True
                micropython.schedule(self._sched_worker, 0)

    def start(self, callback):
        """callback: 普通函数（use_async=False）或轻量回调（use_async=True 下也可）"""
        self._cb = callback
        self.tim.init(period=self.period, mode=Timer.PERIODIC, callback=self._isr)
        return self

    def stop(self):
        self.tim.deinit()
        self._pending = False
        return self

    def reset(self, period_ms=None):
        if period_ms is not None:
            self.period = int(period_ms)
        self.stop()
        self.start(self._cb)
        return self
```

示例：每 1 秒打印一次（硬件定时器，主线程执行回调）

```python
# 文件：main.py
from ticker import Ticker
import time

def heartbeat():
    print("heartbeat")

t = Ticker(period_ms=1000, timer_id=0, use_soft=False, use_async=False).start(heartbeat)

try:
    while True:
        time.sleep_ms(500)
finally:
    t.stop()
```

## 6. 进阶示例：1kHz 采样 + 环形缓冲

- 目标：用 1kHz 定时器采样 GPIO 电平，ISR 中仅写缓冲；主循环批量读取处理。
- 注意：此示例强调结构与方法，实际采样请替换为 ADC/RMT/外设直采以提高性能。

```python
# 文件：sampler.py
from machine import Pin, Timer, disable_irq, enable_irq

class Ring:
    def __init__(self, size):
        self.buf = bytearray(size)
        self.size = size
        self.w = 0
        self.r = 0

    def write_byte(self, v):
        self.buf[self.w] = v
        self.w = (self.w + 1) % self.size
        if self.w == self.r:  # 简易覆盖策略：满缓冲时前移读指针
            self.r = (self.r + 1) % self.size

    def read_chunk(self, n):
        data = bytearray()
        for _ in range(n):
            if self.r == self.w:
                break
            data.append(self.buf[self.r])
            self.r = (self.r + 1) % self.size
        return data

class GPIOSampler:
    def __init__(self, pin_no, period_ms=1, timer_id=1):
        self.pin = Pin(pin_no, Pin.IN)
        self.ring = Ring(2048)
        self.tim = Timer(timer_id)

    def _isr(self, t):
        self.ring.write_byte(self.pin.value())

    def start(self):
        self.tim.init(period=self.period_ms, mode=Timer.PERIODIC, callback=self._isr)

    def stop(self):
        self.tim.deinit()

    def set_period_ms(self, ms):
        self.period_ms = int(ms)

    def fetch(self, n=128):
        state = disable_irq()
        data = self.ring.read_chunk(n)
        enable_irq(state)
        return data
```

使用：

```python
# 文件：main.py
from sampler import GPIOSampler
import time

sam = GPIOSampler(pin_no=34)  # 输入专用脚
sam.set_period_ms(1)          # 1kHz
sam.start()

t0 = time.ticks_ms()
for _ in range(20):
    time.sleep_ms(50)
    chunk = sam.fetch(256)
    print("got", len(chunk), "samples")
dt = time.ticks_diff(time.ticks_ms(), t0)
print("elapsed:", dt, "ms")
sam.stop()
```

## 7. 软件定时器：Timer(-1)

- 优点：不占用硬件定时器，适合大量低精度周期任务。
- 缺点：精度取决于系统节拍，抖动略大，不适合高精度/高频任务。

```python
# 文件：main.py
from machine import Timer
import time

tim = Timer(-1)  # 软件定时器
count = 0

def cb(t):
    global count
    count += 1

tim.init(period=200, mode=Timer.PERIODIC, callback=cb)

t0 = time.ticks_ms()
while count < 10:
    time.sleep_ms(50)
print("ticks:", count, "elapsed:", time.ticks_diff(time.ticks_ms(), t0), "ms")
tim.deinit()
```

## 8. 看门狗（WDT）与定时器的关系（简述）

- `machine.WDT(timeout=ms)`：若主循环在超时前未“喂狗”（`wdt.feed()`），系统将复位。
- 常见做法：用 `Ticker` 或主循环在关键路径定期 `feed()`，确保卡死能被复位。

```python
# 文件：main.py
from machine import WDT
import time

wdt = WDT(timeout=5000)  # 5s 超时
while True:
    # ... 任务 ...
    wdt.feed()           # 正常喂狗
    time.sleep_ms(1000)
```

## 9. 性能与精度建议

- 周期选择：
  - 常规软件心跳 100~~1000ms；中低速任务 10~~100ms；高频任务建议使用硬件定时器或专用外设（RMT/LED PWM/ADC DMA）。
- ISR 最佳实践：
  - 仅做“设标志/计数/极简 I/O”，避免 `print()` 与分配。
  - 用 `micropython.schedule` 或 `ThreadSafeFlag` 将重活移出。
- 计时精度：
  - 需要高精度时间基准时，结合 `time.ticks_us()` 与硬件定时器；`uasyncio` 粒度为 ms。
- 资源管理：
  - 每个 `Timer` 对象独占一个通道；不使用时 `deinit()` 释放。
  - 大项目中为不同模块分配固定 Timer ID，集中管理，避免冲突。

## 10. 常见问题与排查

- 回调不触发或触发紊乱：
  - 确认 `init()` 成功且未被覆盖；检查是否重复使用同一 Timer ID。
- 程序“卡住”或异常：
  - ISR 中做了阻塞或大量打印；迁移逻辑到主线程/协程。
- 抖动明显/时间不准：
  - 使用软件定时器？改用硬件定时器；或增大周期，降低系统负担。
- 资源泄漏：
  - 反复 `init()` 未 `deinit()`；确保退出时释放定时器。
- 与 `uasyncio` 冲突：
  - 不要在 ISR 中直接 `await`；用 `ThreadSafeFlag` 或 `micropython.schedule` 桥接。

## 11. 小结

本章系统介绍了 ESP32 上 `machine.Timer` 的硬/软定时器、ONE_SHOT/周期模式与 ISR 约束，给出闪烁、单次触发、异步联动、环形缓冲采样等实用范例，并提供 `Ticker` 封装以安全地在主线程/协程中执行周期任务。牢记“ISR 只做轻活、重活交给主循环/协程”的原则，可显著提升系统稳定性与可维护性。

---
