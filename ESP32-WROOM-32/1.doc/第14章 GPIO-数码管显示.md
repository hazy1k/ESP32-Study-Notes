# 第十四章 数码管显示

## 1. 导入

数码管（Seven-Segment Display）常见两类：

- 普通数码管（共阳/共阴，1 位或多位）：通过 7 段（a~g）+ 小数点（dp）控制，每段需限流电阻；多位用“位选+段线”动态扫描。
- 驱动芯片方案：TM1637（四位常见）、MAX7219（八位常见）、74HC595（移位寄存器扩展 IO）。

本章分别给出“直连动态扫描”和“TM1637 驱动”的完整实现，并简述 74HC595/MAX7219 用法与工程要点。

## 2. 硬件设计

- 共阴/共阳：
  - 共阴（Common Cathode，CC）：段脚高电平点亮；位选通常高电平使能。
  - 共阳（Common Anode，CA）：段脚低电平点亮；位选通常低电平使能。
- 限流电阻：每个“段（a~~g/dp）”需串入 220~~1kΩ 电阻，禁止“位选侧单电阻多段共用”。
- 多位动态扫描：共享段线，轮流使能位选（每位点亮时间极短，靠余辉与高刷新频率视觉融合）。
- 电流与驱动：多位同时亮段总电流可能较大，必要时位选侧加三极管/阵列（如 ULN2003/2803）。
- 引脚占用：4 位直连需 8 段 + 4 位 = 12 个 IO；用 74HC595 或 TM1637/MAX7219 可大幅节省 IO。
- 典型接线（直连 4 位共阴示例，GPIO 仅示意，按下文代码修改）：

```c
ESP32 GPIOs -> 段线 a,b,c,d,e,f,g,dp（各串 220~1kΩ）-> 数码管段脚
ESP32 GPIOs -> 位选 D1..D4（公阴脚）->（可经 NPN/ULN2003）-> GND
GND 共地
```

## 3. 软件设计

- 关键点：
  - 段码映射（字符→a~g/dp 开关）。
  - 共阳/共阴的“电平反转”。
  - 动态扫描刷新频率（建议每位 200~~1000 Hz/周，整屏 50~~200 Hz，避免闪烁）。
  - 亮度控制：以“占空比”或“跳扫（分段计数跳过点亮）”实现。
- MicroPython 模块：`machine.Pin`、`machine.Timer` 或 `uasyncio` 轮转。

---

## 4. 直连四位数码管：动态扫描（完整可用）

- 特性：4 位、支持小数点、共阳/共阴切换、亮度 0~8、Timer 中断刷新（ISR 极简，不分配）。
- 接线（示例，按需更改）：段线 a,b,c,d,e,f,g,dp → 15,2,0,4,16,17,5,18；位选 D1..D4 → 19,21,22,23。

```python
# 文件：sevenseg_mux.py
from machine import Pin, Timer

# 段序固定为 a,b,c,d,e,f,g,dp
DIGIT_MAP = {
    ' ': 0b00000000,
    '-': 0b01000000,  # g
    '_': 0b00001000,  # d
    '0': 0b00111111,
    '1': 0b00000110,
    '2': 0b01011011,
    '3': 0b01001111,
    '4': 0b01100110,
    '5': 0b01101101,
    '6': 0b01111101,
    '7': 0b00000111,
    '8': 0b01111111,
    '9': 0b01101111,
    'A': 0b01110111,
    'b': 0b01111100,
    'C': 0b00111001,
    'd': 0b01011110,
    'E': 0b01111001,
    'F': 0b01110001,
}

class SevenSegMux:
    def __init__(self, seg_pins, digit_pins, common_anode=False, timer_id=0, refresh_hz=600):
        """
        seg_pins: 长度8的段脚GPIO [a,b,c,d,e,f,g,dp]
        digit_pins: 位选GPIO列表 [D1..Dn]
        common_anode: True 则段脚低电平点亮、位选低电平使能
        refresh_hz: 整屏刷新频率
        """
        assert len(seg_pins) == 8
        self.seg = [Pin(p, Pin.OUT, value=0) for p in seg_pins]
        self.dig = [Pin(p, Pin.OUT, value=0) for p in digit_pins]
        self.ca = bool(common_anode)

        self.n = len(self.dig)
        self.buf = [0] * self.n        # 每位段码（不含小数点）
        self.dp_mask = 0               # 每位小数点位图（bit i）
        self.idx = 0
        self.brightness = 8            # 0..8
        self.pwm_cnt = 0

        self.tim = Timer(timer_id)
        # 每位扫描中断频率 = refresh_hz * 位数
        per_digit_hz = max(200, int(refresh_hz * self.n))
        period_ms = max(1, int(1000 / per_digit_hz))
        self.tim.init(period=period_ms, mode=Timer.PERIODIC, callback=self._isr)

        self._all_digits_off()
        self._apply_segments(0)

    def _all_digits_off(self):
        # 位选“关闭”电平
        off = 1 if not self.ca else 0   # 共阴位选：高=关；共阳位选：低=关
        for d in self.dig:
            d.value(off)

    def _enable_digit(self, i, on):
        # 位选“开启”电平
        en = 0 if not self.ca else 1   # 共阴位选：低=开；共阳位选：高=开
        off = 1 - en
        self.dig[i].value(en if on else off)

    def _apply_segments(self, mask):
        # mask: 0b0dp_gfedcba
        for i, pin in enumerate(self.seg):
            bit_on = (mask >> i) & 1
            if self.ca:
                pin.value(0 if bit_on else 1)  # 共阳：低=亮
            else:
                pin.value(1 if bit_on else 0)  # 共阴：高=亮

    def set_brightness(self, level):
        """0..8（0=熄灭，8=最亮）"""
        level = int(level)
        self.brightness = 0 if level < 0 else 8 if level > 8 else level

    def show_text(self, text, dp_mask=0):
        """
        text: 字符串，最多 n 位；0-9A bCdEF - _ 空格
        dp_mask: 小数点位图，bit0 对应最左位，置1则点亮该位小数点
        """
        s = text[:self.n]
        # 左对齐显示；需要右对齐可自行处理
        self.dp_mask = dp_mask
        for i in range(self.n):
            ch = s[i] if i < len(s) else ' '
            self.buf[i] = DIGIT_MAP.get(ch, 0)

    def show_number(self, value, dp_pos=-1):
        """
        显示整数（或格式化后的小数），dp_pos=小数点位置（0=最左位的右侧）
        """
        s = str(value)
        s = s[-self.n:] if len(s) > self.n else s.rjust(self.n)
        dp_mask = 0
        if 0 <= dp_pos < self.n:
            dp_mask = 1 << (self.n - 1 - dp_pos)
        self.show_text(s, dp_mask)

    def _isr(self, _):
        # PWM 跳扫控制亮度
        self.pwm_cnt = (self.pwm_cnt + 1) % 9
        self._all_digits_off()
        mask = self.buf[self.idx]
        # 小数点位
        if (self.dp_mask >> (self.n - 1 - self.idx)) & 1:
            mask |= 0b10000000
        # 只在 pwm_cnt < brightness 时点亮该位，实现 1/9..8/9 占空
        if self.pwm_cnt < self.brightness and self.brightness > 0:
            self._apply_segments(mask)
            self._enable_digit(self.idx, True)
        self.idx = (self.idx + 1) % self.n

    def close(self):
        self.tim.deinit()
        self._all_digits_off()
        self._apply_segments(0)
```

使用示例：

```python
# 文件：main.py
from sevenseg_mux import SevenSegMux
import time

# 段线 a,b,c,d,e,f,g,dp
SEG_PINS  = [15, 2, 0, 4, 16, 17, 5, 18]
# 位选 D1..D4（从左到右）
DIG_PINS  = [19, 21, 22, 23]

# 共阴示例：common_anode=False；若你的数码管为共阳，设 True 即可（无需改段码）
disp = SevenSegMux(SEG_PINS, DIG_PINS, common_anode=False, timer_id=0, refresh_hz=120)

try:
    disp.set_brightness(6)
    disp.show_text("12-3", dp_mask=0b0010)  # 第二位小数点
    time.sleep(2)

    # 计数演示
    for v in range(0, 1234, 7):
        disp.show_number(v)
        time.sleep(0.03)

    # 温度样式：23.5
    disp.show_text("235 ", dp_mask=0b0100)  # 23.5
    time.sleep(2)

finally:
    disp.close()
```

要点：

- 若出现“鬼影/串色”，增大 `refresh_hz` 或检查位选/段脚顺序；必要时位选侧加三极管阵列。
- 亮度通过“跳扫占空”实现，不改变段电流（更稳定）。

---

## 5. TM1637 四位数码管（常见“时钟”式）

- 仅需 2 个 GPIO（CLK/DIO），板上自带限流与扫描，亮度 0~7。
- 接线（示例）：`CLK -> GPIO22`，`DIO -> GPIO21`，`VCC 5V`，`GND 共地`。

```python
# 文件：tm1637.py
from machine import Pin
import time

# 基本段码（不含 dp），顺序 a,b,c,d,e,f,g
SEG = {
    ' ': 0x00, '-': 0x40,
    '0': 0x3f, '1': 0x06, '2': 0x5b, '3': 0x4f, '4': 0x66,
    '5': 0x6d, '6': 0x7d, '7': 0x07, '8': 0x7f, '9': 0x6f,
    'A': 0x77, 'b': 0x7c, 'C': 0x39, 'd': 0x5e, 'E': 0x79, 'F': 0x71,
}

class TM1637:
    def __init__(self, clk, dio, brightness=7):
        self.clk = Pin(clk, Pin.OUT, value=1)
        self.dio = Pin(dio, Pin.OUT, value=1)
        self.set_brightness(brightness)

    def _start(self):
        self.dio.init(Pin.OUT)
        self.dio.value(1); self.clk.value(1)
        self.dio.value(0); self.clk.value(0)

    def _stop(self):
        self.dio.init(Pin.OUT)
        self.dio.value(0); self.clk.value(1); self.dio.value(1)

    def _write_byte(self, b):
        for i in range(8):
            self.dio.value((b >> i) & 1)
            self.clk.value(1); self.clk.value(0)
        # 读 ACK（可忽略）
        self.dio.init(Pin.IN)
        self.clk.value(1)
        _ = self.dio.value()
        self.clk.value(0)
        self.dio.init(Pin.OUT)

    def set_brightness(self, level):
        # 0..7
        self.brightness = 0 if level < 0 else 7 if level > 7 else int(level)

    def show(self, s, colon=False):
        s = s[:4].ljust(4)
        data = []
        for i, ch in enumerate(s):
            v = SEG.get(ch, 0)
            # 第二位的 dp 常作为冒号（部分板子固定连在中间冒号）
            if colon and i == 1:
                v |= 0x80
            data.append(v)
        # 写数据（自动地址增加）
        self._start(); self._write_byte(0x40); self._stop()
        # 写起始地址 0xC0
        self._start(); self._write_byte(0xC0)
        for v in data:
            self._write_byte(v)
        self._stop()
        # 显示控制（显示开 + 亮度）
        self._start(); self._write_byte(0x88 | self.brightness); self._stop()
```

使用示例：

```python
# 文件：main.py
from tm1637 import TM1637
import time

tm = TM1637(clk=22, dio=21, brightness=4)

# 显示时间样式
for i in range(20):
    tm.show("12{:02d}".format(i), colon=(i % 2 == 0))
    time.sleep(0.5)

# 显示整数
tm.show(" 123", colon=False)
time.sleep(1)
tm.show("-5  ", colon=False)
```

优势：省 IO、亮度稳定、无须自己扫描。注意部分模块供电 5V，需与 ESP32 共地。

---

## 6. 备选方案速览

- 74HC595 扩展 IO：
  - 用 1 片驱动段线（8 位），位选直接 IO；或两片级联（一片段、一片位），使用 3 线（CLK/LATCH/DATA）即可驱动 4~8 位。
  - 速度要求不高可用软件位移；更高可用 `machine.SPI`。
- MAX7219（8 位七段/点阵）：
  - SPI 接口，初始化后设置“解码模式/扫描范围/亮度”；用“Code B 解码”可直接写数字与 `-`。
  - 供电与散热、接地要好，链式连接可扩展位数。
  - 参考寄存器：`0x09` 解码、`0x0A` 亮度、`0x0B` 扫描位数、`0x0C` 关/开、`0x01..0x08` 各位数据。

---

## 7. 工程与调试要点

- 刷新与亮度：
  - 动态扫描的“整屏刷新”≥50 Hz（建议 100~200 Hz）避免闪烁；亮度以占空实现更稳。
- 共阴/共阳：
  - 段码不变，通过“电平反转”适配；位选电平也需对应调整。
- 电流与限流：
  - 每段必须单独限流；多位模块建议位选侧加晶体管/达林顿阵列分担电流。
- 布线与干扰：
  - 段线/位选走线短、并加地参考；若用长线与电机等共存，适当加 RC 或缓冲。
- 字符集与布局：
  - 七段天然不适合字母全量显示，控制期待值；必要时用“滚动/闪烁”表达更多信息。

## 8. 小结

本章实现了直连四位数码管的动态扫描（含亮度调制与小数点）、TM1637 的两线驱动（含冒号与亮度），并给出 74HC595 与 MAX7219 的选型要点。通过合理的段码映射、电平反转与刷新策略，可以稳定、低成本地完成数字/状态信息的可视化显示。

---
