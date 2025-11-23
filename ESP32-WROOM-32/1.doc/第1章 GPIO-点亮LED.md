# 第一章 GPIO-点亮LED

## 1. 导入

点亮一个 LED 是学习 ESP32 + MicroPython 的最佳起点。通过这个实验，你将完成从环境搭建、引脚连接到编写与运行代码的完整闭环，并为后续的闪烁、流水灯与 PWM 呼吸灯做铺垫。

## 2. 开发准备

- 驱动与端口：
  - Windows：安装 USB 转串口驱动（常见为 CP210x 或 CH34x），端口形如 `COM3`。
  - macOS：端口通常是 `/dev/tty.SLAB_USBtoUART` 或 `/dev/tty.usbserial-*`。
  - Linux：端口通常是 `/dev/ttyUSB0` 或 `/dev/ttyACM0`。
- 固件获取：到 MicroPython 官网下载适配 ESP32 的 `.bin` 固件。
- 烧录工具：`esptool.py` 或使用 Thonny 快速烧录均可。
- 开发软件：Thonny、mpremote、rshell 均可，入门推荐 Thonny 或官方的 `mpremote`。

烧录固件（示例，按你实际端口与文件名替换）：

```bash
# 擦除
esptool.py --chip esp32 --port COM3 --baud 460800 erase_flash
# 写入固件
esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 esp32-2024xxxx-v1.xx.x.bin
```

连接 REPL：

```bash
mpremote connect COM3
# 或 Linux/macOS
mpremote connect /dev/ttyUSB0
```

## 3. 硬件设计

- 本实验硬件：
  - LED 模块中的 D1 指示灯
  - ESP32 开发板若干 GPIO
- 原理说明：J1 为 LED 控制端，高电平点亮（常见）。将 ESP32 的某个 GPIO 接 J1，GND 共地，即可用软件控制亮灭。
- 建议接线：

```c
LED 模块 --> ESP32 IO
D1       --> GPIO15   （本章示例）
GND      --> GND
VCC      --> 3.3V     （若 LED 模块需供电）
```

- 多路预留（为后续流水灯准备，当前仅需 D1→GPIO15）：

```c
LED 模块 --> ESP32 IO
(D1-D8)  --> (15, 2, 0, 4, 16, 17, 5, 18)
```

- 注意事项：
  - 启动绑带脚：GPIO0/GPIO2/GPIO15 影响启动模式，量产或复杂项目建议改用安全 GPIO（如 4/5/16/17/18/19/21/22/23/25/26/27/32/33）。
  - 电平逻辑：若你的 LED 模块是“低电平点亮”，则输出 0 点亮，输出 1 熄灭。
  - 板卡丝印与 GPIO：某些开发板标注 `Dxx` 与真实 GPIO 不同，请以“GPIO 编号”为准。

## 4. 软件设计

### 4.1 实验目标

- 点亮一个 LED（D1）。
- 理解 `machine.Pin` 的基本用法。

### 4.2 `Pin` 基本用法

- 导入方式：
  - `import machine` 后用 `machine.Pin(...)`
  - `from machine import Pin` 后直接 `Pin(...)`（本章采用）
- 常用构造与方法：
  - `Pin(n, Pin.OUT, value=0)`：配置为输出，设初值
  - `p.value(1/0)`：置高/低电平
  - `p.on()/p.off()`：便捷方法（等价于设 1/0）

## 5. 编写与运行

### 5.1 最小可用示例（点亮）

```python
# 文件：main.py
from machine import Pin

def main():
    led = Pin(15, Pin.OUT, value=0)  # 先确保熄灭
    led.value(1)                     # 高电平点亮（若为低电平点亮，请改为 0）

if __name__ == "__main__":
    main()
```

### 5.2 让 LED 闪烁（阻塞式）

```python
# 文件：main.py
from machine import Pin
import time

def main():
    led = Pin(15, Pin.OUT)
    while True:
        led.value(1)
        time.sleep(0.5)
        led.value(0)
        time.sleep(0.5)

if __name__ == "__main__":
    main()
```

### 5.3 使用定时器闪烁（非阻塞）

```python
# 文件：main.py
from machine import Pin, Timer
import time

led = Pin(15, Pin.OUT)
tim = Timer(0)

def _toggle(_):
    led.value(1 - led.value())

def main():
    tim.init(period=500, mode=Timer.PERIODIC, callback=_toggle)
    # 主循环仍可做其他工作
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
```

提示：定时器回调在中断上下文中执行，避免在回调里分配大量内存或做耗时操作。

### 5.4 使用 uasyncio 闪烁（协程）

```python
# 文件：main.py
from machine import Pin
import uasyncio as asyncio

led = Pin(15, Pin.OUT)

async def blink(period=0.5):
    while True:
        led.value(1 - led.value())
        await asyncio.sleep(period)

def main():
    asyncio.run(blink())

if __name__ == "__main__":
    main()
```

### 5.5 LED 类封装（兼容高/低电平点亮）

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

```python
# 文件：main.py
from led import LED
import time

def main():
    led = LED(15, active_high=True)
    while True:
        led.toggle()
        time.sleep(0.3)

if __name__ == "__main__":
    main()
```

### 5.6 流水灯（为后续章节预热）

```python
# 文件：main.py
from led import LED
import time

PINS = [15, 2, 0, 4, 16, 17, 5, 18]  # 如果担心启动脚，换成 4,16,17,5,18,19,21,22 等

def main():
    leds = [LED(p, active_high=True) for p in PINS]
    while True:
        for l in leds:
            l.on()
            time.sleep(0.08)
            l.off()

if __name__ == "__main__":
    main()
```

### 5.7 PWM 呼吸灯（亮度渐变）

```python
# 文件：main.py
from machine import Pin, PWM
import time

def set_duty(pwm, duty_10bit):
    # 兼容不同固件：优先使用 duty()（0..1023），否则退化到 duty_u16()
    try:
        pwm.duty(duty_10bit)
    except AttributeError:
        pwm.duty_u16(int(duty_10bit * 65535 / 1023))

def main():
    pwm = PWM(Pin(15), freq=1000)
    try:
        while True:
            for d in range(0, 1024, 8):
                set_duty(pwm, d)
                time.sleep(0.01)
            for d in range(1023, -1, -8):
                set_duty(pwm, d)
                time.sleep(0.01)
    finally:
        pwm.deinit()

if __name__ == "__main__":
    main()
```

## 6. 常见问题与排查

- LED 不亮：
  - 检查共地（GND 必须相连）。
  - 确认使用的是真实 GPIO 编号而非板载 `Dxx` 丝印。
  - 模块是低电平点亮？尝试把 `value(1)` 改为 `value(0)`。
  - 引脚是否被占用或焊接不良，或为输入模式。
- 上电无法启动或 USB 枚举异常：
  - 避免在上电时对 GPIO0/GPIO2/GPIO15 施加强拉电平或重负载。
  - 移除外接 LED 再试，或改用安全 GPIO。
- REPL 无法连接：
  - 端口号是否正确，是否被占用（如串口监视器未关闭）。
  - 线缆更换与供电检查。

## 7. 实验拓展

- 改写闪烁频率为可配置参数（如通过串口输入或读取配置文件）。
- 将流水灯封装成类，支持方向与速度切换。
- 与按键结合：按键切换 LED 模式（常亮/闪烁/呼吸）。

## 8. 小结

本章完成了从固件烧录、REPL 连接、GPIO 输出控制到多种点灯方式（常亮、闪烁、定时器、协程、PWM 呼吸）的全流程；掌握了 `Pin` 的核心用法、电平逻辑与启动脚注意事项，并给出了可复用的 LED 类与典型示例。

---
