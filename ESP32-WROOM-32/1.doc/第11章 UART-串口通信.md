# 第十一章 串口通信（UART）

## 1. 导入

串口（UART）是最常用、最简单稳定的有线通信方式之一，常用于与 PC、GPS、蓝牙串口模块、外部 MCU 等设备交换数据。ESP32 拥有 3 个硬件 UART（0/1/2），MicroPython 提供 `machine.UART` 进行配置和读写。本章从硬件接线、基础 API、阻塞/非阻塞/中断接收到常见桥接与简单协议，系统讲解 UART 的正确打开方式与避坑要点。

## 2. 硬件设计

- 电平标准：
  - ESP32 串口是 3.3V TTL 电平；严禁直接接 RS-232 电平（±12V）。
  - 与 5V 设备相连需确认其 UART 是否 3.3V 兼容；否则加电平转换。
- 交叉连接与共地：
  - `ESP32 TX -> 对方 RX`，`ESP32 RX -> 对方 TX`，`GND <-> GND`。
- 引脚与编号：
  - `UART(0)` 默认为 REPL/下载口（GPIO1=TX0，GPIO3=RX0，经板载 USB 转串口），不建议用于外设通信。
  - 建议使用 `UART(1)` / `UART(2)`，并显式指定 `tx`/`rx` 引脚（ESP32 引脚矩阵几乎可任意映射）。
  - GPIO34–39 为输入专用脚，仅可作 RX，不可作 TX。
  - 避免启动相关脚（0/2/15）及板载用途冲突的脚。
- 可选硬件流控：
  - 某些设备支持 RTS/CTS，可在构造时传入 `rts=`、`cts=`，提高高波特率可靠性。

典型外设接线（以 UART2 为例）：

```c
ESP32 GPIO17 (TX2) --> 设备 RX
ESP32 GPIO16 (RX2) <-- 设备 TX
ESP32 GND          <--> 设备 GND
```

## 3. 基础 API 与快速上手

- 构造与配置：
  - `UART(id, baudrate=9600, bits=8, parity=None, stop=1, tx=None, rx=None, timeout=1000, timeout_char=10, rxbuf=2048, txbuf=0, invert=0, flow=0)`
- 读写：
  - `uart.write(b'hello')` 返回写入字节数
  - `uart.read(n)` 读最多 n 字节；`uart.read()` 读全部缓冲
  - `uart.readline()` 按行读（以 `\n` 结尾）
  - `uart.any()` 返回接收缓冲中的字节数（是否有数据）

### 3.1 最小示例（回环自测）

用跳线把 TX 与 RX 短接（仅测试用），发什么收什么。

```python
# 文件：main.py
from machine import UART, Pin
import time

# 使用 UART2，显式指定引脚（按你的接线修改）
uart = UART(2, baudrate=115200, tx=17, rx=16, timeout=200)

while True:
    s = "hello {}\n".format(time.ticks_ms())
    uart.write(s.encode())
    time.sleep(0.2)
    if uart.any():
        data = uart.readline()
        if data:
            print("echo:", data)
```

### 3.2 与 PC 通信（第二路串口）

- 将 USB 线连接电脑用于供电与 REPL；另用外接 USB-TTL 转串口模块连到 `UART(1/2)`。
- 用 PC 串口终端（115200 8N1，无流控）打开对应端口，即可收发。

发送一行，读取并打印：

```python
# 文件：main.py
from machine import UART
import time

uart = UART(1, baudrate=115200, tx=4, rx=5, timeout=200)

while True:
    # 非阻塞检查
    if uart.any():
        line = uart.readline()
        if line:
            print("PC->ESP32:", line.decode(errors="ignore").strip())
            uart.write(b"ACK:" + line)  # 回显确认
    time.sleep(0.01)
```

## 4. 读取模式对比

### 4.1 阻塞式读取（简单直观）

```python
# 文件：main.py
from machine import UART

uart = UART(2, 9600, tx=17, rx=16, timeout=500)  # 超时 500ms

while True:
    line = uart.readline()  # 等待直到超时或读到 '\n'
    if line:
        print("got:", line)
```

- 简单但会“等数据”阻塞主循环，不适合并发任务。

### 4.2 轮询式非阻塞（常用）

```python
# 文件：main.py
from machine import UART
import time

uart = UART(2, 115200, tx=17, rx=16, timeout=50)

buf = bytearray()

while True:
    n = uart.any()
    if n:
        chunk = uart.read(n)
        if chunk:
            buf.extend(chunk)
            # 处理按行协议
            while True:
                i = buf.find(b"\n")
                if i < 0:
                    break
                line = bytes(buf[:i+1]); del buf[:i+1]
                print("line:", line.decode(errors="ignore").strip())
    # 其他任务...
    time.sleep(0.005)
```

### 4.3 中断式接收（UART.irq）

在 ISR 内仅“搬运到缓冲”，避免重逻辑。

```python
# 文件：uart_irq_demo.py
from machine import UART
import time

uart = UART(2, 115200, tx=17, rx=16, timeout=0, rxbuf=2048)

rxbuf = bytearray()
def _isr(u):
    # 尽量短小：读出尽可能多的数据放入缓冲
    while u.any():
        ch = u.read(1)
        if ch:
            rxbuf.extend(ch)

uart.irq(handler=_isr)  # 默认 RX_ANY 触发

while True:
    # 主循环里解析
    while True:
        i = rxbuf.find(b"\n")
        if i < 0:
            break
        line = bytes(rxbuf[:i+1]); del rxbuf[:i+1]
        print("line:", line.decode(errors="ignore").strip())
    time.sleep(0.01)
```

### 4.4 uasyncio 非阻塞读（协程）

MicroPython 没有标准 UART Stream，常用“轮询 + sleep_ms”实现协程读。

```python
# 文件：main.py
from machine import UART
import uasyncio as asyncio

uart = UART(2, 115200, tx=17, rx=16, timeout=0)

async def reader():
    buf = bytearray()
    while True:
        n = uart.any()
        if n:
            buf.extend(uart.read(n) or b"")
            while True:
                i = buf.find(b"\n")
                if i < 0:
                    break
                line = bytes(buf[:i+1]); del buf[:i+1]
                print("RX:", line.decode(errors="ignore").strip())
        await asyncio.sleep_ms(5)

async def writer():
    i = 0
    while True:
        msg = "tick {}\n".format(i).encode()
        uart.write(msg)
        i += 1
        await asyncio.sleep(1)

async def main():
    await asyncio.gather(reader(), writer())

asyncio.run(main())
```

## 5. 实用封装与示例

### 5.1 行协议收发器（带缓冲）

```python
# 文件：serial_line.py
from machine import UART

class SerialLine:
    def __init__(self, id, *, baud=115200, tx=None, rx=None, rxbuf=2048, timeout=100):
        self.uart = UART(id, baudrate=baud, tx=tx, rx=rx, timeout=timeout, rxbuf=rxbuf)
        self.buf = bytearray()

    def send_line(self, s: str):
        if not s.endswith("\n"):
            s += "\n"
        return self.uart.write(s.encode())

    def read_lines(self):
        """返回本轮解析出的所有完整行(list[str])，无阻塞"""
        out = []
        n = self.uart.any()
        if n:
            data = self.uart.read(n)
            if data:
                self.buf.extend(data)
                while True:
                    i = self.buf.find(b"\n")
                    if i < 0:
                        break
                    line = bytes(self.buf[:i+1]); del self.buf[:i+1]
                    out.append(line.decode(errors="ignore").rstrip("\r\n"))
        return out
```

使用：

```python
# 文件：main.py
from serial_line import SerialLine
import time

sl = SerialLine(2, baud=115200, tx=17, rx=16)
while True:
    for ln in sl.read_lines():
        print(">", ln)
        sl.send_line("ACK:" + ln)
    time.sleep(0.01)
```

### 5.2 串口桥接（USB<->外设）

将 UART2 与 USB-REPL 之间互转，可调试外设（如 GPS、蓝牙 SPP 模块）。

```python
# 文件：bridge.py
from machine import UART
import sys, time

# UART2 外设侧
u2 = UART(2, 9600, tx=17, rx=16, timeout=0)

# 从 USB-REPL(stdin) 到 UART2
def stdin_to_uart():
    n = sys.stdin.buffer.read()  # 可能阻塞；不同固件行为不同
    if n:
        u2.write(n)

# 从 UART2 到 stdout
def uart_to_stdout():
    n = u2.any()
    if n:
        sys.stdout.write((u2.read(n) or b"").decode(errors="ignore"))

while True:
    uart_to_stdout()
    # 视固件支持情况，stdin 的非阻塞读取可能不可用；可换行缓冲策略
    time.sleep(0.01)
```

说明：不同固件对 `sys.stdin.buffer.read()` 的行为不一致，若阻塞，建议在 PC 侧使用两个终端分别连接 USB-REPL 与外部 USB-TTL，而在板端仅转发 UART2→stdout。

## 6. 配置与协议要点

- 参数匹配：
  - 波特率、数据位、校验位、停止位需与对端一致（常用 115200 8N1）。
  - 长报文可适当增大 `rxbuf`，避免溢出丢字节。
- 编码与帧边界：
  - 建议统一 UTF-8 文本或二进制协议；文本协议用 `\n` 分行易解析。
  - 二进制协议需自定义帧头/长度/校验；示例：`[0xAA,0x55,len,payload...,crc]`。
- 流控与可靠性：
  - 大量高速数据建议启用 RTS/CTS 硬件流控（前提是对端支持）。
  - 软件侧控制写入速率，必要时在应用层加 ACK/重传。
- 资源管理：
  - 不再使用的 UART 对象无需特别释放；但改变配置应重新构造或 `init()`。

## 7. 常见问题与排查

- 收不到数据：
  - TX/RX 是否交叉、GND 是否共地、波特率是否一致。
  - RX 引脚是否用了输入专用脚（34–39 可作 RX，不可作 TX）。
  - 线过长或干扰强，波特率过高可导致误码，先降为 9600 测试。
- 中文/乱码：
  - 确认编码一致（UTF-8）；终端显示编码需匹配。
- 偶发丢字节：
  - `rxbuf` 太小或读取不及时；增大缓冲并加快读取频率。
  - 波特率过高且无流控；尝试开 RTS/CTS 或降低波特率。
- 与 REPL 冲突：
  - 避免占用 `UART(0)`；使用 `UART(1/2)` 并显式指定引脚。

## 8. 小结

本章介绍了 ESP32 上 UART 的硬件接线、电平规范与 `machine.UART` 的核心用法，分别给出阻塞、轮询、IRQ 与协程等多种读取方案，并提供了行协议收发器与串口桥接示例。结合合理的缓冲、帧边界与必要的流控策略，即可稳定地与 PC、外设或其他 MCU 进行串口通信。

---
