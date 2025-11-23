# 第五章 按键开关

## 1. 导入

按键是最常见的人机交互输入。相比输出型外设（LED、继电器），按键的难点在于“消抖”（机械触点在按下/松开瞬间会跳变多次）以及“多种手势识别”（单击、双击、长按）。本章将从硬件接法到软硬件消抖、轮询/中断/uasyncio 三种实现方式，再到支持单击/双击/长按的通用 `Button` 类封装，一步步实现稳定可靠的按键输入。

## 2. 硬件设计

- 典型接线（推荐上拉输入，按下接地）：

```c
ESP32 GPIO（输入，上拉） <---> 按键 <---> GND
                         |
                         +-- 内部上拉（Pin.PULL_UP）或外部上拉电阻（10kΩ）
```

- 选择 GPIO：
  - 避免使用启动相关脚：GPIO0/GPIO2/GPIO15（开发板自带 BOOT 常在 GPIO0）。
  - 推荐安全 GPIO：4/5/16/17/18/19/21/22/23/25/26/27/32/33。
- 有无外部电阻：
  - 可用 ESP32 内部上拉/下拉（`Pin.PULL_UP`/`Pin.PULL_DOWN`），简单省料。
  - 噪声环境可加外部 10kΩ 上拉/下拉、电容 100nF 并联做 RC 硬件消抖（软件仍建议保留 10–30ms 消抖）。
- 线长/干扰：
  - 按键连线尽量短；必要时加小电容、屏蔽线或软件增加消抖窗口。

## 3. 软件设计

### 3.1 实验目标

- 稳定读取按键状态，掌握上拉输入与电平逻辑。
- 实现消抖与事件识别：单击、双击、长按。
- 对比与掌握三种方案：轮询、外部中断、uasyncio 协程。

### 3.2 关键模块

- `machine.Pin`：GPIO 输入、上拉/下拉、IRQ 中断。
- `time`：`sleep_ms`、`ticks_ms`、`ticks_diff` 精确计时。
- `uasyncio`：非阻塞扫描与事件并发处理。

---

## 4. 快速上手：最小读取 + 简单消抖（轮询）

常见接法为“上拉输入，按下为低”。示例使用 `GPIO13`（可改）。

```python
# 文件：main.py
from machine import Pin
import time

KEY_PIN = 13
# 上拉输入：未按下=1，按下=0
key = Pin(KEY_PIN, Pin.IN, Pin.PULL_UP)

def wait_release():
    # 等待完全松开，避免“连发”
    while key.value() == 0:
        time.sleep_ms(10)

def main():
    print("Press the button on GPIO", KEY_PIN)
    while True:
        if key.value() == 0:          # 检测到低电平
            time.sleep_ms(20)         # 消抖
            if key.value() == 0:      # 二次确认
                print("Pressed")
                wait_release()
                print("Released")
        time.sleep_ms(10)

if __name__ == "__main__":
    main()
```

要点：

- 使用内部上拉：`Pin.IN, Pin.PULL_UP`。
- 按下为低（Active Low）；若“按下为高”，改用 `Pin.PULL_DOWN` 并调整判断。

---

## 5. 中断方式（IRQ）+ 软件消抖

中断能在边沿变化时立刻响应，主循环不必频繁轮询。注意：中断回调要短小，禁用耗时操作（如 `print` 过多、分配大内存、阻塞等待）。

```python
# 文件：main.py
from machine import Pin
import time

KEY_PIN = 13
key = Pin(KEY_PIN, Pin.IN, Pin.PULL_UP)

last_ms = 0
DEBOUNCE_MS = 30

def on_falling(pin):  # 按下（上拉输入：下降沿）
    global last_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ms) > DEBOUNCE_MS:
        # 在中断里只做标记或极少量工作
        print("Pressed (IRQ)")  # 若串口刷屏，可改为设置标志位
        last_ms = now

# 监听下降沿（按下）
key.irq(trigger=Pin.IRQ_FALLING, handler=on_falling)

# 主循环可继续做其他任务
while True:
    time.sleep_ms(200)
```

---

## 6. uasyncio 非阻塞扫描（推荐）

协程方式便于与其他任务并发，易于实现“单击/双击/长按”等手势。

```python
# 文件：main.py
from machine import Pin
import uasyncio as asyncio
import time

KEY_PIN = 13
DEBOUNCE_MS = 30
DOUBLE_MS = 250
LONG_MS = 800

key = Pin(KEY_PIN, Pin.IN, Pin.PULL_UP)

def is_pressed():
    return key.value() == 0  # 上拉输入，低为按下

async def button_task(on_click, on_double, on_long):
    prev = is_pressed()
    last_change = time.ticks_ms()
    t_down = None
    click_pending = False
    last_click_up = 0

    while True:
        cur = is_pressed()
        now = time.ticks_ms()

        # 状态变化并消抖
        if cur != prev and time.ticks_diff(now, last_change) > DEBOUNCE_MS:
            last_change = now
            prev = cur
            if cur:  # 由未按->按下
                t_down = now
            else:    # 由按下->松开
                if t_down is not None:
                    dur = time.ticks_diff(now, t_down)
                    if dur >= LONG_MS:
                        await on_long()
                        click_pending = False
                    else:
                        # 候选一次单击
                        if click_pending and time.ticks_diff(now, last_click_up) <= DOUBLE_MS:
                            await on_double()
                            click_pending = False
                        else:
                            click_pending = True
                            last_click_up = now
                    t_down = None

        # 单击确认（在双击窗口到时后触发）
        if click_pending and time.ticks_diff(now, last_click_up) > DOUBLE_MS and not is_pressed():
            await on_click()
            click_pending = False

        await asyncio.sleep_ms(5)

async def main():
    async def on_click():  print("CLICK")
    async def on_double(): print("DOUBLE")
    async def on_long():   print("LONG")
    task = asyncio.create_task(button_task(on_click, on_double, on_long))
    await asyncio.gather(task)

asyncio.run(main())
```

---

## 7. 封装：Button 类（单击/双击/长按/回调）

提供统一电平逻辑、去抖、事件回调，默认适配“上拉输入、按下为低”。

```python
# 文件：button.py
from machine import Pin
import time
try:
    import uasyncio as asyncio
except ImportError:
    asyncio = None

class Button:
    def __init__(self, pin,
                 pull=Pin.PULL_UP,
                 active_low=True,
                 debounce_ms=30,
                 double_ms=250,
                 long_ms=800):
        self.pin = Pin(pin, Pin.IN, pull) if pull is not None else Pin(pin, Pin.IN)
        self.active_low = active_low
        self.debounce_ms = debounce_ms
        self.double_ms = double_ms
        self.long_ms = long_ms

        self._on_press = None
        self._on_release = None
        self._on_click = None
        self._on_double = None
        self._on_long = None

        self._prev = self.is_pressed()
        self._last_change = time.ticks_ms()
        self._t_down = None
        self._click_pending = False
        self._last_click_up = 0

        self._task = None

    def is_pressed(self):
        v = self.pin.value()
        return (v == 0) if self.active_low else (v == 1)

    # 注册事件回调（协程函数或普通函数均可）
    def on_press(self, cb):   self._on_press = cb;   return self
    def on_release(self, cb): self._on_release = cb; return self
    def on_click(self, cb):   self._on_click = cb;   return self
    def on_double(self, cb):  self._on_double = cb;  return self
    def on_long(self, cb):    self._on_long = cb;    return self

    async def _call(self, cb):
        if cb is None: return
        if asyncio and hasattr(cb, "__call__") and asyncio.iscoroutinefunction(cb):
            await cb()
        else:
            cb()

    async def _run(self):
        while True:
            cur = self.is_pressed()
            now = time.ticks_ms()

            if cur != self._prev and time.ticks_diff(now, self._last_change) > self.debounce_ms:
                self._last_change = now
                self._prev = cur
                if cur:
                    self._t_down = now
                    await self._call(self._on_press)
                else:
                    await self._call(self._on_release)
                    if self._t_down is not None:
                        dur = time.ticks_diff(now, self._t_down)
                        if dur >= self.long_ms:
                            await self._call(self._on_long)
                            self._click_pending = False
                        else:
                            if self._click_pending and time.ticks_diff(now, self._last_click_up) <= self.double_ms:
                                await self._call(self._on_double)
                                self._click_pending = False
                            else:
                                self._click_pending = True
                                self._last_click_up = now
                        self._t_down = None

            if self._click_pending and time.ticks_diff(now, self._last_click_up) > self.double_ms and not self.is_pressed():
                await self._call(self._on_click)
                self._click_pending = False

            if asyncio:
                await asyncio.sleep_ms(5)
            else:
                time.sleep_ms(5)

    def start(self):
        if asyncio is None:
            raise RuntimeError("uasyncio 不可用，无法 start 协程；请直接调用 step() 轮询")
        if self._task is None:
            self._task = asyncio.create_task(self._run())
        return self

    # 若项目未使用 uasyncio，可在循环中频繁调用 step() 实现轮询
    def step(self):
        # 简化版轮询入口，单步推进状态机
        # 供无 uasyncio 环境使用（每 5~10ms 调用一次）
        cur = self.is_pressed()
        now = time.ticks_ms()
        if cur != self._prev and time.ticks_diff(now, self._last_change) > self.debounce_ms:
            self._last_change = now
            self._prev = cur
            if cur:
                self._t_down = now
                if self._on_press: self._on_press()
            else:
                if self._on_release: self._on_release()
                if self._t_down is not None:
                    dur = time.ticks_diff(now, self._t_down)
                    if dur >= self.long_ms:
                        if self._on_long: self._on_long()
                        self._click_pending = False
                    else:
                        if self._click_pending and time.ticks_diff(now, self._last_click_up) <= self.double_ms:
                            if self._on_double: self._on_double()
                            self._click_pending = False
                        else:
                            self._click_pending = True
                            self._last_click_up = now
                    self._t_down = None

        if self._click_pending and time.ticks_diff(now, self._last_click_up) > self.double_ms and not self.is_pressed():
            if self._on_click: self._on_click()
            self._click_pending = False
```

示例 1：uasyncio 版本，单击切换 LED，长按常亮，双击熄灭

```python
# 文件：main.py
from machine import Pin
import uasyncio as asyncio
from button import Button

LED_PIN = 15
BTN_PIN = 13

led = Pin(LED_PIN, Pin.OUT, value=0)

async def on_click():
    led.value(1 - led.value())  # 翻转

async def on_double():
    led.value(0)  # 双击熄灭

async def on_long():
    led.value(1)  # 长按常亮

async def main():
    btn = Button(BTN_PIN, pull=Pin.PULL_UP, active_low=True).on_click(on_click).on_double(on_double).on_long(on_long)
    btn.start()
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
```

示例 2：无 uasyncio 环境，轮询驱动 `step()`

```python
# 文件：main.py
from machine import Pin
import time
from button import Button

LED_PIN = 15
BTN_PIN = 13

led = Pin(LED_PIN, Pin.OUT, value=0)

def on_click():
    led.value(1 - led.value())

def on_long():
    led.value(1)

def main():
    btn = Button(BTN_PIN, pull=Pin.PULL_UP, active_low=True)
    btn.on_click(on_click).on_long(on_long)
    while True:
        btn.step()         # 每次推进一次状态机
        time.sleep_ms(5)   # 扫描周期

if __name__ == "__main__":
    main()
```

---

## 8. 常见问题与排查

- 按下无反应或乱触发：
  - 电平逻辑不符：若接“上拉输入，按下接地”，应设置 `Pin.PULL_UP` 且 `active_low=True`。
  - 消抖时间过短：机械按键建议 20–50ms；测试环境可从 30ms 起调。
  - 线太长/干扰：加 100nF 电容就地消抖，或提高软件消抖时间。
- 上电即被判定按下：
  - 启动瞬间脚位浮空；务必使用上拉/下拉，初始化后先读取并忽略短时间内的状态。
- 中断回调异常或死机：
  - 回调内禁止阻塞/大量 `print`；只记标志，实际处理放到主循环/协程。
- 使用开发板 BOOT 键（GPIO0）：
  - 作为普通按键可用，但按下复位时会影响启动模式；建议选用其它 GPIO。

## 9. 小结

本章完成了按键的硬件接线与电平逻辑说明，给出了轮询、中断和 uasyncio 三种读取方式，并通过 `Button` 类实现了单击、双击与长按等常见手势的稳定识别。通过合理的消抖参数与事件封装，按键可与 LED、蜂鸣器、继电器等外设可靠联动。

---
