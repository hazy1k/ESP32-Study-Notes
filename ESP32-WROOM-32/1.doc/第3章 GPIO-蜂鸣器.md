# 第三章 蜂鸣器

## 1. 导入

蜂鸣器常见两种类型：有源蜂鸣器（Active Buzzer）和无源蜂鸣器（Passive Buzzer）。

- 有源蜂鸣器：内部自带振荡电路，只需给高/低电平即可响；适合“滴——”提示音。
- 无源蜂鸣器：需要指定频率的方波驱动（PWM），可发出不同音高；适合“音阶/旋律”。

本章将分别给出两类蜂鸣器的接线与代码，覆盖“单次蜂鸣、可调频蜂鸣（音调）、旋律播放、阻塞/非阻塞（协程）”等常见需求。

## 2. 硬件设计

- 硬件资源：
  - 有源蜂鸣器模块 或 无源蜂鸣器（压电式）
  - ESP32 若干 GPIO
- 典型接线（推荐用安全 GPIO，如 `GPIO25` 或 `GPIO26`）：

```c
有源蜂鸣器模块（带驱动）
SIG/IN  --> GPIO25
VCC     --> 3.3V
GND     --> GND
```

```c
无源蜂鸣器模块（或裸压电片，建议带限流/驱动）
SIG/IN  --> GPIO25（将用于 PWM）
VCC     --> 3.3V
GND     --> GND
```

- 注意事项：
  - 模块若标注“LOW 有效”，则低电平触发响，代码需设置 `active_high=False`。
  - 裸蜂鸣器电流可能超过单片机 IO 能力，尽量使用带驱动的蜂鸣器模块，或外加三极管+限流电阻驱动。
  - 启动脚 GPIO0/GPIO2/GPIO15 参与启动模式，建议避免；选用 4/5/16/17/18/19/21/22/23/25/26/27/32/33 等。
  - 无源蜂鸣器要发声必须使用 PWM 输出合适频率（人耳敏感 2–4 kHz）。

## 3. 软件设计

### 3.1 实验目标

- 有源蜂鸣器：控制“响/不响”，实现可配置的“嘀”提示音。
- 无源蜂鸣器：用 PWM 产生音调（频率），实现音阶与旋律。
- 掌握阻塞式与 `uasyncio` 协程式两种时序方式。

### 3.2 关键模块

- `machine.Pin`：GPIO 输出（有源蜂鸣器）
- `machine.PWM`：PWM 输出（无源蜂鸣器）
- `time`：简单延时
- `uasyncio`：协程并发和非阻塞时序

---

## 4. 快速上手

### 4.1 有源蜂鸣器：最小示例（滴一声）

```python
# 文件：main.py
from machine import Pin
import time

def beep_once(pin=25, active_high=True, ms=200):
    buz = Pin(pin, Pin.OUT, value=0 if active_high else 1)  # 先静音
    buz.value(1 if active_high else 0)  # 触发响
    time.sleep(ms / 1000)
    buz.value(0 if active_high else 1)  # 关闭

if __name__ == "__main__":
    beep_once(pin=25, active_high=True, ms=200)
```

### 4.2 无源蜂鸣器：最小示例（1000 Hz）

```python
# 文件：main.py
from machine import Pin, PWM
import time

def tone_once(pin=25, freq=1000, ms=300, duty=0.5):
    pwm = PWM(Pin(pin))
    pwm.freq(freq)
    # 兼容不同固件的 duty 接口
    try:
        pwm.duty(int(1023 * duty))      # 0..1023
    except AttributeError:
        pwm.duty_u16(int(65535 * duty)) # 0..65535
    time.sleep(ms / 1000)
    try:
        pwm.duty(0)
    except AttributeError:
        pwm.duty_u16(0)
    pwm.deinit()

if __name__ == "__main__":
    tone_once(pin=25, freq=2000, ms=300)
```

---

## 5. 封装：Buzzer 类（同时支持有源/无源）

```python
# 文件：buzzer.py
from machine import Pin, PWM
import time

class Buzzer:
    def __init__(self, pin, kind="active", active_high=True, default_freq=2000):
        """
        kind: "active" 有源蜂鸣器，"passive" 无源蜂鸣器
        active_high: True-高电平响, False-低电平响（有源时生效）
        default_freq: 无源蜂鸣器默认频率
        """
        self.pin_no = pin
        self.kind = kind
        self.active_high = active_high
        self.default_freq = default_freq
        self._pin = Pin(pin, Pin.OUT)
        self._pwm = None
        self.silence()

    # 兼容不同固件的 PWM 占空比设置
    def _set_duty_frac(self, pwm, frac):
        frac = max(0.0, min(1.0, float(frac)))
        try:
            pwm.duty(int(1023 * frac))
        except AttributeError:
            pwm.duty_u16(int(65535 * frac))

    def _ensure_pwm(self):
        if self._pwm is None:
            self._pwm = PWM(self._pin)

    def silence(self):
        if self.kind == "active":
            self._pin.value(0 if self.active_high else 1)
        else:
            if self._pwm:
                self._set_duty_frac(self._pwm, 0.0)

    # 有源：直接拉电平；无源：默认频率 + 50% 占空比
    def on(self, duty=0.5):
        if self.kind == "active":
            self._pin.value(1 if self.active_high else 0)
        else:
            self._ensure_pwm()
            self._pwm.freq(self.default_freq)
            self._set_duty_frac(self._pwm, duty)

    def off(self):
        self.silence()

    # 有源：定长“嘀”；无源：用默认频率发声
    def beep(self, ms=150, duty=0.5):
        self.on(duty=duty)
        time.sleep(ms / 1000)
        self.off()

    # 无源专用：指定频率与时长（有源也可用，但频率无意义）
    def tone(self, freq, ms=200, duty=0.5):
        if self.kind == "passive":
            self._ensure_pwm()
            self._pwm.freq(int(freq))
            self._set_duty_frac(self._pwm, duty)
            time.sleep(ms / 1000)
            self._set_duty_frac(self._pwm, 0.0)
        else:
            # 有源蜂鸣器忽略频率，仅按时长“嘀”
            self.beep(ms=ms, duty=duty)

    # 旋律播放：melody 为 [(freq_or_name, beat), ...]；tempo 为 BPM
    def play(self, melody, tempo=120, duty=0.5):
        # 简易音名到频率表（等温律近似）
        NOTES = {
            "C4": 262, "D4": 294, "E4": 330, "F4": 349, "G4": 392, "A4": 440, "B4": 494,
            "C5": 523, "D5": 587, "E5": 659, "F5": 698, "G5": 784, "A5": 880, "B5": 988,
            "R": 0  # 休止
        }
        beat_sec = 60.0 / float(tempo)  # 四分音符时长
        for n, beat in melody:
            duration = beat_sec * float(beat)
            if isinstance(n, str):
                freq = NOTES.get(n.upper(), 0)
            else:
                freq = int(n)
            if freq <= 0:
                self.off()
                time.sleep(duration)
            else:
                self.tone(freq=freq, ms=int(duration * 1000), duty=duty)

    def close(self):
        self.off()
        if self._pwm:
            self._pwm.deinit()
            self._pwm = None
```

示例 1：有源蜂鸣器“嘀嘀”提示音

```python
# 文件：main.py
from buzzer import Buzzer
import time

def main():
    buz = Buzzer(pin=25, kind="active", active_high=True)
    for _ in range(3):
        buz.beep(ms=120)
        time.sleep(0.15)
        buz.beep(ms=120)
        time.sleep(0.6)
    buz.close()

if __name__ == "__main__":
    main()
```

示例 2：无源蜂鸣器播放音阶与旋律

```python
# 文件：main.py
from buzzer import Buzzer
import time

MELODY_TWINKLE = [
    ("C4",1), ("C4",1), ("G4",1), ("G4",1), ("A4",1), ("A4",1), ("G4",2),
    ("F4",1), ("F4",1), ("E4",1), ("E4",1), ("D4",1), ("D4",1), ("C4",2),
]

def main():
    buz = Buzzer(pin=25, kind="passive", default_freq=2000)
    # 简单音阶
    for f in (262,294,330,349,392,440,494,523):
        buz.tone(freq=f, ms=200)
        time.sleep(0.05)
    # 小星星
    buz.play(MELODY_TWINKLE, tempo=140, duty=0.5)
    buz.close()

if __name__ == "__main__":
    main()
```

---

## 6. 协程版（uasyncio）：非阻塞蜂鸣模式

适合与其他任务并行运行（如 LED 效果、传感器轮询）。

```python
# 文件：main.py
from buzzer import Buzzer
import uasyncio as asyncio

async def beep_pattern(buz: Buzzer, on_ms=100, off_ms=200, repeat=10):
    for _ in range(repeat):
        buz.on()
        await asyncio.sleep(on_ms / 1000)
        buz.off()
        await asyncio.sleep(off_ms / 1000)
    buz.off()

async def siren(buz: Buzzer, f1=600, f2=1400, step=40, dwell_ms=12):
    # 无源蜂鸣器：上下扫频形成“警笛”
    while True:
        for f in range(f1, f2, step):
            buz.tone(freq=f, ms=dwell_ms)
            await asyncio.sleep(0)  # 让出调度
        for f in range(f2, f1, -step):
            buz.tone(freq=f, ms=dwell_ms)
            await asyncio.sleep(0)

async def main():
    # 有源：用 beep_pattern；无源：可试 siren
    buz_active = Buzzer(pin=25, kind="active", active_high=True)
    buz_passive = Buzzer(pin=26, kind="passive", default_freq=1800)

    t1 = asyncio.create_task(beep_pattern(buz_active, 80, 120, repeat=12))
    t2 = asyncio.create_task(siren(buz_passive, f1=700, f2=1300, step=30, dwell_ms=10))
    await asyncio.sleep(5)  # 运行 5 秒
    for t in (t1, t2):
        t.cancel()
    buz_active.close(); buz_passive.close()

asyncio.run(main())
```

---

## 7. 实验拓展

- 为 `Buzzer.play` 增加八度、升降号与更完整的音名解析。
- 根据环境噪声自动调节音量（通过占空比）或选择不同提示音方案。
- 与按键/传感器结合：不同事件播放不同“提示音”或“旋律”。

## 8. 常见问题与排查

- 无声或很小：
  - 无源蜂鸣器需 PWM；确认使用了 `PWM(Pin(...))` 并设置了合适的 `freq` 与 `duty`。
  - 占空比过低或频率不在 2000–4000 Hz 附近，可尝试 `duty=0.3~0.7`、`freq=2k~3k`。
  - 模块为“低电平有效”？将 `active_high=False`。
- 上电自鸣或噪声：
  - 上电引脚悬空导致误触发；初始化时先设为“静音”态，必要时外接下拉电阻。
  - PWM 未 `deinit` 或占空比未清零会持续微响；调用 `off()` 或 `close()`。
- GPIO 损坏风险：
  - 裸蜂鸣器直接接 IO 可能过流，优先使用带驱动模块，或加三极管+电阻。

## 9. 小结

本章区分了有源与无源蜂鸣器的原理与用法：有源用 GPIO 电平即可发声，无源需 PWM 输出指定频率。我们实现了单次蜂鸣、可调音调、旋律播放与协程式非阻塞控制，并提供统一的 `Buzzer` 封装，便于在项目中复用与扩展。

---
