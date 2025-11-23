# 第四章 继电器

## 1. 导入

继电器用于用低压微控器控制高电压/大电流负载，是物联网与家居自动化的常见器件。常见类型包括：

- 机械继电器（MR）：线圈+机械触点，隔离好，可切 AC/DC，大功率，带触点抖动与机械寿命。
- 固态继电器（SSR）：半导体开关，无机械声，寿命长；注意漏电流、发热、对应 AC/DC 的型号限制。

本章以“ESP32 + 继电器模块”为例，给出高/低电平触发的控制方法、时序控制（定时与协程）、多路控制与安全要点。

## 2. 硬件设计

- 硬件资源：
  - 单路/多路继电器模块（推荐带光耦、三极管、二极管、跳线）
  - ESP32 开发板（3.3V 逻辑）
- 模块触发逻辑：
  - 高电平触发（Active-High）：IN=1 吸合，IN=0 释放
  - 低电平触发（Active-Low）：IN=0 吸合，IN=1 释放（不少“光耦隔离”模块属于此类）
- 电源与接线（机械继电器模块常见做法）：

```c
继电器模块       --> ESP32
IN（信号）        --> GPIO4（示例，可换安全 GPIO）
GND              --> GND（共地）
VCC（逻辑供电）   --> 3.3V 或 5V（看模块要求，很多支持 5V）
JD-VCC（线圈供电）--> 5V（可选，带“跳线帽”模块可将 JD-VCC 与 VCC 隔离）
```

- 触点端子（负载侧）：COM、NO、NC
  - NO（常开）：继电器吸合时与 COM 导通
  - NC（常闭）：继电器释放时与 COM 导通
- 重要安全提示：
  - 切断市电操作，避免触电；保持高压侧与低压侧的安全距离与绝缘，外壳防护必须到位。
  - 机械继电器切感性负载（马达、电磁阀）会有火花与尖峰，使用 RC 吸收网络/压敏/TVS 抑制，必要时用专业继电器或接触器。
  - 不要用 ESP32 IO 直接驱动裸线圈，必须使用带驱动的继电器模块或外加三极管+二极管。
  - 模块为光耦完全隔离时，若使用 JD-VCC 独立线圈供电，可去掉逻辑地共地；若无隔离或使用单电源，ESP32 GND 与模块 GND 必须共地。

## 3. 软件设计

### 3.1 实验目标

- 控制继电器吸合/释放，实现定时脉冲与安全关断。
- 兼容“高/低电平触发”模块的逻辑封装。
- 多路继电器顺序开关与非阻塞控制。

### 3.2 关键模块

- `machine.Pin`：GPIO 输出控制
- `time`：阻塞式延时
- `uasyncio`：协程并发与非阻塞时序

---

## 4. 快速上手

### 4.1 最小示例（低电平触发模块）

不少继电器模块为低电平触发，IN 拉低吸合。

```python
# 文件：main.py
from machine import Pin
import time

def main():
    relay = Pin(4, Pin.OUT, value=1)  # 低电平触发：默认拉高=断开
    # 吸合 1 秒
    relay.value(0)
    time.sleep(1)
    # 释放
    relay.value(1)

if __name__ == "__main__":
    main()
```

### 4.2 最小示例（高电平触发模块）

```python
# 文件：main.py
from machine import Pin
import time

def main():
    relay = Pin(4, Pin.OUT, value=0)  # 高电平触发：默认拉低=断开
    relay.value(1)                    # 吸合 1 秒
    time.sleep(1)
    relay.value(0)                    # 释放

if __name__ == "__main__":
    main()
```

---

## 5. 封装：Relay 类（统一“触发电平”）

```python
# 文件：relay.py
from machine import Pin
import time

class Relay:
    def __init__(self, pin, active_high=False, init_off=True):
        """
        pin: GPIO 号
        active_high: True 表示高电平吸合；False 表示低电平吸合（常见）
        init_off: 初始化后是否确保断开
        """
        self.pin = Pin(pin, Pin.OUT)
        self.active_high = bool(active_high)
        if init_off:
            self.off()

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

    def pulse(self, ms=200):
        """吸合 ms 毫秒后自动释放（阻塞式）"""
        self.on()
        time.sleep(ms / 1000)
        self.off()

    def on_for(self, ms=1000):
        """吸合指定时长后释放（阻塞式）"""
        self.pulse(ms)
```

示例：基本控制与脉冲

```python
# 文件：main.py
from relay import Relay
import time

def main():
    # 低电平触发模块：active_high=False
    r = Relay(pin=4, active_high=False)
    r.on_for(500)       # 吸合 0.5s
    time.sleep(0.5)
    r.on(); time.sleep(2); r.off()

if __name__ == "__main__":
    main()
```

---

## 6. 协程与非阻塞控制（uasyncio）

适合在不阻塞其他任务（如传感器读取/网络通信）的情况下定时控制继电器。

```python
# 文件：main.py
from relay import Relay
import uasyncio as asyncio

async def pulse_async(relay: Relay, ms=200, gap_ms=800, repeat=5):
    for _ in range(repeat):
        relay.on()
        await asyncio.sleep(ms / 1000)
        relay.off()
        await asyncio.sleep(gap_ms / 1000)

async def hold_async(relay: Relay, hold_ms=3000):
    relay.on()
    await asyncio.sleep(hold_ms / 1000)
    relay.off()

async def main():
    r1 = Relay(pin=4, active_high=False)  # 低电平触发
    r2 = Relay(pin=5, active_high=True)   # 高电平触发

    t1 = asyncio.create_task(pulse_async(r1, ms=150, gap_ms=350, repeat=10))
    t2 = asyncio.create_task(hold_async(r2, hold_ms=5000))
    await asyncio.gather(t1, t2)

asyncio.run(main())
```

---

## 7. 多路继电器与顺序控制

多路模块（2/4/8 路）常用于多负载控制。建议顺序吸合避免浪涌。

```python
# 文件：relay_array.py
from relay import Relay
import time

class RelayArray:
    def __init__(self, pins, active_high=False):
        self.relays = [Relay(p, active_high=active_high) for p in pins]
        self.all_off()

    def all_on(self, step_ms=0):
        for r in self.relays:
            r.on()
            if step_ms > 0:
                time.sleep(step_ms / 1000)

    def all_off(self, step_ms=0):
        for r in self.relays:
            r.off()
            if step_ms > 0:
                time.sleep(step_ms / 1000)

    def chase_on(self, on_ms=300, gap_ms=100):
        for r in self.relays:
            r.on(); time.sleep(on_ms / 1000); r.off()
            time.sleep(gap_ms / 1000)
```

示例：4 路顺序吸合

```python
# 文件：main.py
from relay_array import RelayArray

# 尽量使用安全 GPIO，如 4,16,17,5,18,19,21,22,23
PINS = [4, 16, 17, 5]

def main():
    arr = RelayArray(PINS, active_high=False)  # 假设为低电平触发模块
    arr.chase_on(on_ms=300, gap_ms=120)
    arr.all_on(step_ms=50)
    arr.all_off(step_ms=50)

if __name__ == "__main__":
    main()
```

---

## 8. 安全与工程建议

- 供电与地线：
  - 继电器线圈电流较大（几十到上百 mA），不要从 ESP32 3.3V 给线圈供电；使用模块的 5V 接口或独立 5V 电源。
  - 若使用 JD-VCC 光耦隔离，线圈供电与逻辑供电隔离；按模块说明正确拔插跳线，必要时取消共地。
- 电磁干扰（ESP32 复位/死机）：
  - 继电器动作会带来反向尖峰与电源跌落。为 ESP32 端加大电解+陶瓷去耦（如 100µF + 0.1µF），继电器端靠近线圈放置二极管/吸收回路（模块通常内置）。
  - 对市电与感性负载，使用 RC 吸收、压敏器件或专业浪涌抑制。
  - 电源分离：继电器线圈用独立 5V，ESP32 用稳定 5V/3.3V，必要时做星形接地。
- 启动与误触发：
  - 避免使用 ESP32 启动相关 GPIO（0/2/15）或在上电即吸合的逻辑；若模块低电平触发，初始化时先写入“释放电平”。
- SSR 注意：
  - AC SSR 多为过零型，适合阻性负载（灯泡/加热丝），对感性/低功率可能有残余电流导致微亮；DC SSR 要匹配负载电压电流范围。

## 9. 常见问题与排查

- 继电器不吸合：
  - 模块需要 5V 线圈供电？确认供电与电流能力；确认 IN 电平是否满足触发条件（3.3V 有些模块边缘触发不足）。
  - 低电平触发却输出高电平？检查并设置 `active_high=False`。
- 吸合抖动/异响频繁：
  - 电源跌落/地弹；加强供电与地线、缩短高电流回路、加大去耦。
- ESP32 复位：
  - 与继电器共电源、负载浪涌大；做电源隔离/吸收/独立供电；检查 USB 供电能力。
- 负载不工作或反逻辑：
  - NO/NC 接错；核对负载接法与触点定义。

## 10. 小结

本章区分了高/低电平触发的继电器模块，给出了最小示例、统一封装的 `Relay` 类、协程式非阻塞控制以及多路顺序控制。重点强调了高压侧的安全、电磁干扰与供电隔离等工程要点，确保在实际项目中稳定可靠地驱动各类负载。

---
