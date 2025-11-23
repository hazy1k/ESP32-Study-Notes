# 第十九章 超声波测距

## 1. 导入

超声波测距通过发射超声脉冲、测量回波飞行时间来得到目标距离。常见模块包括脉冲型（Trig/Echo，如 HC‑SR04、JSN‑SR04T）与串口型（US‑100、A02YYUW 等）。本章给出两类模块的可靠接线、完整驱动与稳健测距封装，并提供“水位测量”和“舵机雷达扫描”两个实战示例。

- 距离公式（考虑往返时间）：
  - LaTeX：`d = \frac{t \cdot v}{2}`
  - 其中 `t` 为回波高电平持续时间（秒），`v` 为声速（m/s）。
  - 20°C 近似换算：LaTeX：`d_{cm} \approx t_{us} \times 0.01715`

## 2. 方案与传感器类型

- 脉冲型（Trig/Echo）：
  - HC‑SR04：室内常用，2–400cm，性价比高。
  - JSN‑SR04T：防水探头，布线更灵活（部分版本支持 UART 模式）。
- 串口型（UART）：
  - US‑100：9600bps，支持串口读距或“Trig/Echo”两种模式。
  - A02YYUW：9600bps，连续输出或帧格式输出（不同批次协议略有差异）。
- 注意与选择：
  - 室内通用：HC‑SR04；户外/水位：JSN‑SR04T（防水）。
  - 电磁噪声/线长：优先串口型或带缓冲电源处理。
  - 多只同时使用：避免串扰，建议轮询触发。

## 3. 硬件连接

- 供电：
  - 模块多为 `VCC=5V`，ESP32 与模块共地。
- 电平安全（重中之重）：
  - HC‑SR04 Echo 输出为 5V，禁止直连 3.3V 引脚；请用分压或电平转换后接 ESP32。
  - US‑100/A02YYUW 串口一般为 3.3V/5V 兼容 TTL，确认手册再直连。
- Echo 分压示例：

```c
Echo(5V) ---- 10kΩ ----+----> ESP32 GPIO(ECHO)
                        |
                       20kΩ
                        |
                       GND
# 5V * (20k / (10k+20k)) ≈ 3.3V
```

---

## 4. 通用工具：温度补偿与滤波

```python
# 文件：sonar_utils.py
def sound_coeff_cm_per_us(temp_c=20.0):
    """
    返回 (cm/us)/2 系数（已包含/2），用于 d_cm = t_us * coeff
    v = 331.3 + 0.606*T（m/s），换算到 cm/us 并除以2
    """
    v = 331.3 + 0.606 * float(temp_c)   # m/s
    return (v * 100) / 1_000_000 / 2    # (cm/us)/2

def median(values):
    a = sorted(values)
    n = len(a)
    return a[n//2] if n else None

class IIR:
    def __init__(self, alpha=0.2, init=None):
        self.a = float(alpha)
        self.y = init
    def step(self, x):
        if x is None:
            return self.y
        x = float(x)
        if self.y is None:
            self.y = x
        else:
            self.y += self.a * (x - self.y)
        return self.y
```

---

## 5. 驱动一：Trig/Echo（HC‑SR04/JSN‑SR04T）

```python
# 文件：hcsr04.py
from machine import Pin, time_pulse_us
import time
from sonar_utils import sound_coeff_cm_per_us

class HCSR04:
    def __init__(self, trig, echo, *, echo_pull=None,
                 timeout_us=30000, min_period_ms=60, temp_c=20.0):
        """
        trig: GPIO（输出）
        echo: GPIO（输入，5V 需分压）
        echo_pull: Pin.PULL_DOWN/PULL_UP 或 None
        timeout_us: 超时对应最大量程（400cm ≈ 23ms）
        min_period_ms: 最小测量周期，避免串扰
        temp_c: 温度用于声速补偿
        """
        self.trig = Pin(trig, Pin.OUT, value=0)
        self.echo = Pin(echo, Pin.IN, echo_pull) if echo_pull else Pin(echo, Pin.IN)
        self.timeout = int(timeout_us)
        self.min_period = int(min_period_ms)
        self.temp_c = float(temp_c)
        self._last_ms = 0

    def _pulse(self):
        # 清旧回波（非必需，尽量“吸收”残留）
        try:
            time_pulse_us(self.echo, 1, 800)
        except OSError:
            pass
        # 触发 10us 高电平
        self.trig.value(0); time.sleep_us(2)
        self.trig.value(1); time.sleep_us(10)
        self.trig.value(0)
        # 计时（高电平持续）
        return time_pulse_us(self.echo, 1, self.timeout)

    def distance_cm_once(self, *, temp_c=None):
        # 周期限速
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self._last_ms)
        if dt < self.min_period:
            time.sleep_ms(self.min_period - dt)
        self._last_ms = time.ticks_ms()

        try:
            t = self._pulse()  # us
        except OSError:
            return None
        coeff = sound_coeff_cm_per_us(self.temp_c if temp_c is None else temp_c)
        return t * coeff

    def distance_cm_median(self, n=5, *, temp_c=None):
        n = max(1, int(n) | 1)  # 奇数
        arr = []
        for _ in range(n):
            d = self.distance_cm_once(temp_c=temp_c)
            if d is not None:
                arr.append(d)
        if not arr:
            return None
        arr.sort()
        return arr[len(arr)//2]
```

---

## 6. 驱动二：UART 超声波（US‑100 / A02YYUW）

```python
# 文件：uart_sonar.py
from machine import UART
import time

class US100UART:
    """
    US-100 串口模式（9600,8N1）
    - 发送 0x55，返回 2 字节：高/低，单位 mm
    - 读数为 0 或异常时返回 None
    """
    def __init__(self, uart_id=2, tx=None, rx=None, baud=9600, timeout=100):
        self.uart = UART(uart_id, baudrate=baud, tx=tx, rx=rx, timeout=timeout)

    def distance_cm(self):
        self.uart.write(bytes([0x55]))
        t0 = time.ticks_ms()
        while self.uart.any() < 2 and time.ticks_diff(time.ticks_ms(), t0) < self.uart.timeout:
            time.sleep_ms(2)
        data = self.uart.read(2) or b""
        if len(data) != 2:
            return None
        mm = (data[0] << 8) | data[1]
        if mm == 0 or mm > 10000:
            return None
        return mm / 10.0

class A02YYUW:
    """
    A02YYUW 常见帧：0xFF, HIGH, LOW, SUM；单位 mm
    SUM = (0xFF + HIGH + LOW) & 0xFF
    一些版本连续输出；此处轮询读取并解析最后一帧
    """
    def __init__(self, uart_id=2, tx=None, rx=None, baud=9600, timeout=100):
        self.uart = UART(uart_id, baudrate=baud, tx=tx, rx=rx, timeout=timeout)

    def _read_frame(self, timeout_ms=100):
        t0 = time.ticks_ms()
        # 简单同步到 0xFF
        while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
            if self.uart.any():
                b = self.uart.read(1)
                if b and b[0] == 0xFF:
                    rest = self.uart.read(3) or b""
                    if len(rest) == 3:
                        high, low, s = rest
                        if ((0xFF + high + low) & 0xFF) == s:
                            return (high << 8) | low
            time.sleep_ms(2)
        return None

    def distance_cm(self):
        mm = self._read_frame()
        if mm is None or mm == 0 or mm > 10000:
            return None
        return mm / 10.0
```

---

## 7. 稳定测距封装（统一入口）

```python
# 文件：ranger.py
import time
from sonar_utils import IIR
from hcsr04 import HCSR04
from uart_sonar import US100UART, A02YYUW

class Ranger:
    """
    统一测距接口：支持 HCSR04/US100/A02YYUW
    - median 次数 + IIR 平滑
    - 限幅（最大跳变）
    """
    def __init__(self, sensor, *, median_n=5, iir_alpha=0.25, max_step_cm=None):
        self.sensor = sensor
        self.median_n = int(median_n)
        self.filt = IIR(alpha=iir_alpha)
        self.max_step = float(max_step_cm) if max_step_cm else None
        self._last = None

    def read_cm(self):
        if isinstance(self.sensor, HCSR04):
            d = self.sensor.distance_cm_median(n=self.median_n)
        elif isinstance(self.sensor, (US100UART, A02YYUW)):
            # 串口型无需多次触发，简化为单次读取多次取中值
            arr = []
            for _ in range(self.median_n):
                v = self.sensor.distance_cm()
                if v is not None:
                    arr.append(v)
            d = sorted(arr)[len(arr)//2] if arr else None
        else:
            raise TypeError("未知传感器类型")

        # 限幅
        if d is not None and self._last is not None and self.max_step is not None:
            if abs(d - self._last) > self.max_step:
                d = self._last + self.max_step * (1 if d > self._last else -1)
        self._last = d if d is not None else self._last

        # IIR 平滑
        return self.filt.step(d)
```

使用示例：

```python
# 文件：main.py
from hcsr04 import HCSR04
from uart_sonar import US100UART, A02YYUW
from ranger import Ranger
import time

# 任选其一（按接线替换）
sonar = HCSR04(trig=5, echo=18, min_period_ms=70, temp_c=25.0)
# sonar = US100UART(uart_id=2, tx=17, rx=16)
# sonar = A02YYUW(uart_id=2, tx=17, rx=16)

r = Ranger(sonar, median_n=5, iir_alpha=0.2, max_step_cm=30)

while True:
    d = r.read_cm()
    print("d={:.1f} cm".format(d) if d is not None else "d=None")
    time.sleep(0.12)
```

---

## 8. 应用一：水位测量（顶部下射）

假设传感器固定于水箱顶部，空箱时“底到传感器距离”为 `D_empty`，水箱高度 `H`。测距为 `d` 时，水位高度：

- LaTeX：`level = \operatorname{clip}(H - (d - D_{empty}),\, 0,\, H)`

圆柱形水箱体积（升）：

- LaTeX：`V(L) = \frac{\pi r^2 \cdot level}{1000}`（`r`、`level` 单位 cm）

```python
# 文件：water_level.py
from ranger import Ranger
from hcsr04 import HCSR04
import math, time

# 实测标定（单位 cm）
D_EMPTY = 95.0     # 空箱距
H_TANK  = 80.0     # 水箱有效高度
R_TANK  = 30.0     # 圆柱半径

sonar = HCSR04(trig=5, echo=18, min_period_ms=70, temp_c=25.0)
r = Ranger(sonar, median_n=5, iir_alpha=0.25, max_step_cm=20)

def calc_level(d_cm):
    if d_cm is None:
        return None, None
    level = H_TANK - (d_cm - D_EMPTY)
    level = 0.0 if level < 0 else H_TANK if level > H_TANK else level
    volume_l = math.pi * (R_TANK**2) * level / 1000.0
    return level, volume_l

while True:
    d = r.read_cm()
    level, vol = calc_level(d)
    if level is None:
        print("no echo")
    else:
        print("d={:.1f}cm, level={:.1f}cm, vol={:.1f}L".format(d, level, vol))
    time.sleep(0.2)
```

提示：

- 防溅板：水面波动时可在探头下方加一小块平面反射板（与水面保持足够高度差），提升稳定性。
- 温度补偿：若有温度传感器（如 DS18B20），可将温度实时传给 `HCSR04(..., temp_c=...)` 或在读取时覆盖 `temp_c=`。

---

## 9. 应用二：舵机雷达扫描

- SG90/FS90 舵机：50Hz，脉宽 0.5–2.5ms 对应 0–180°。
- 步进扫描：每 2–3° 测一次，取中值滤波，形成极坐标“扇形点云”。

```python
# 文件：servo_radar.py
from machine import Pin, PWM
import time
from hcsr04 import HCSR04

SERVO_PIN = 14
FREQ = 50  # Hz
MIN_US, MAX_US = 500, 2500

def set_duty_frac(pwm, frac):
    # 兼容 duty()/duty_u16()
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else float(frac)
    try:
        pwm.duty(int(1023 * frac))
    except AttributeError:
        pwm.duty_u16(int(65535 * frac))

class Servo:
    def __init__(self, pin, freq=50, min_us=500, max_us=2500):
        self.pwm = PWM(Pin(pin), freq=freq)
        self.freq = freq
        self.min_us, self.max_us = min_us, max_us
    def write_deg(self, deg):
        deg = 0 if deg < 0 else 180 if deg > 180 else deg
        us = self.min_us + (self.max_us - self.min_us) * (deg / 180.0)
        period_us = 1_000_000 / self.freq
        set_duty_frac(self.pwm, us / period_us)
    def deinit(self):
        try: set_duty_frac(self.pwm, 0.0)
        except: pass
        self.pwm.deinit()

sonar = HCSR04(trig=5, echo=18, min_period_ms=70, temp_c=25.0)
servo = Servo(SERVO_PIN, freq=FREQ, min_us=MIN_US, max_us=MAX_US)

def scan_once(a0=20, a1=160, step=2, settle_ms=180):
    pts = []
    for deg in list(range(a0, a1+1, step)) + list(range(a1, a0-1, -step)):
        servo.write_deg(deg)
        time.sleep_ms(settle_ms)
        d = sonar.distance_cm_median(n=3)
        pts.append((deg, None if d is None else round(d,1)))
    return pts

try:
    while True:
        data = scan_once()
        # 简单文本“柱状”展示
        for deg, d in data:
            if d is None or d > 300:
                bar = ""
            else:
                bar = "#" * int(d/4)
            print("{:3d}° {:5}".format(deg, bar))
        print("---- sweep end ----")
        time.sleep(0.5)
finally:
    servo.deinit()
```

提示：

- 机械回差会带来少量角度偏移，可在正扫/反扫分别标定纠偏。
- 扫描频率不宜过快：舵机需要稳定时间、超声测距需要≥60ms 周期。

---

## 10. 常见问题与排查

- Echo 直连 3.3V 引脚：
  - 高风险！务必分压或电平转换；损伤不可逆。
- 总是 None/超时：
  - 物体超量程或软质吸声；供电不足；触发过快导致上一回波未消散。
- 抖动大/离群值多：
  - 增加 `min_period_ms`；使用中值与 IIR；改善安装角度（尽量垂直）与供电去耦。
- 多只传感器互扰：
  - 串行轮询触发，间隔 ≥60ms；物理隔离或错位安装。
- 防水探头（JSN‑SR04T）近距离盲区：
  - 盲区通常更大（20–30cm），按手册设置量程与位置。
- 与 Wi‑Fi 并发：
  - 降低刷新率；关键读数处做重试与滤波；必要时改用串口型或固件底层捕获（RMT，若固件支持）。

---

## 11. 小结

本章构建了“超声波测距”的完整链路：安全接线、电平转换、Trig/Echo 与 UART 两类模块的驱动、统一的稳健测距封装与滤波，并落地到“水位测量”和“舵机雷达扫描”。实战中请牢记电气安全（Echo 分压）、测距节奏（≥60ms）、中值+IIR 平滑与温度补偿，基本即可获得稳定、可复用的测距能力。需要更高刷新与精准度时，可考虑硬件串口型或在固件侧使用 RMT/定时捕获进行微秒级测量。

---
