# 第十二章 ADC 采集电压

## 1. 导入

ADC（模数转换器）用于把模拟电压转换为数字值。ESP32 内置两组 ADC：

- ADC1：GPIO32–39（推荐，稳定，Wi‑Fi 可用时不受影响）
- ADC2：GPIO0/2/4/12–15/25–27（与 Wi‑Fi 共用，Wi‑Fi 活动时读取可能失败）

本章讲解硬件接法、MicroPython 的 `machine.ADC` 用法、衰减/量程、噪声抑制与滤波、多通道扫描、定时采样，以及通过分压测量高于 1.1V 的电压，并给出电压换算与简单标定方法。

## 2. 硬件设计

- 安全电压：ADC 引脚最大不得超过 `3.3V`（绝对上限略高但请勿逼近）。
- 量程与衰减：ESP32 的 ADC 输入默认近 `1.1V` 满量程，需设置衰减扩大量程（见软件设计）。
- 高电压测量：用电阻分压把被测电压降到 ADC 允许范围，并加 RC 小滤波提升稳定性：

```c
Vin ---- R1 ----+---- R2 ---- GND
                |
              ADCx
                |
               C(100nF~1uF) // 到 GND（提升抗噪）
```

- 建议电阻：总阻值 50kΩ～200kΩ 量级（过大将使 ADC 输入阻抗太高影响精度，过小增加功耗）。
- 共地：被测电路与 ESP32 必须共地。

分压换算公式（R1 上端接被测电压，R2 下端接地，ADC 在中间）：

- 理论关系：`Vadc = Vin * R2 / (R1 + R2)`
- 求被测电压：
  - 以 LaTeX 表达：`Vin = Vadc \cdot \frac{R1 + R2}{R2}`

## 3. 软件设计

### 3.1 实验目标

- 配置 ADC 衰减与分辨率，读取原始数值。
- 将原始值换算为电压（含分压比）。
- 多次采样平均/中值/一阶 IIR 滤波，获得稳定值。
- 多通道轮询与定时采样。

### 3.2 关键 API（MicroPython）

- 构造：`adc = ADC(Pin(x))`
- 衰减：`adc.atten(ADC.ATTN_0DB | 2_5DB | 6DB | 11DB)`
  - 0dB ≈ 1.1V；2.5dB ≈ 1.5V；6dB ≈ 2.2V；11dB ≈ 3.3~3.9V（芯片差异）
- 分辨率：
  - 老固件：`adc.width(ADC.WIDTH_12BIT)`（9/10/11/12 位）
  - 新固件常固定 12 位；`width()` 可能不可用
- 读取：
  - `adc.read()`：0..4095（12 位）
  - `adc.read_u16()`：0..65535（标度到 16 位）

说明：ESP32 ADC 受工艺偏差影响，绝对精度较差，需通过标定或软件修正；但相对变化与平均值可用。

---

## 4. 快速上手：单通道读取 + 换算电压

示例：用 ADC1 GPIO34（输入专用脚）测电压，设置 11dB（量程到 3.3V 左右）。

```python
# 文件：main.py
from machine import ADC, Pin
import time

PIN = 34  # 推荐 ADC1: 32~39（34~39 为输入专用）
adc = ADC(Pin(PIN))

# 配置衰减到最大（~3.3V 量程），不同固件常量名一致
adc.atten(ADC.ATTN_11DB)

# 宽度：有些固件可设，有些固定 12bit；尝试设置，不支持则忽略
try:
    adc.width(ADC.WIDTH_12BIT)
except:
    pass

def read_raw():
    try:
        return adc.read()  # 0..4095
    except:
        return adc.read_u16() >> 4  # 16位缩到 12位

def raw_to_voltage(raw, vref=1100, atten='11db'):
    """
    raw: 0..4095
    vref: mV（芯片内部参考电压典型 1100mV，不同片差异较大）
    atten: 用于粗略换算的衰减档位
    返回单位：V
    """
    # 衰减系数近似（满量程 ≈ k * vref）
    k = {
        '0db': 1.00,
        '2.5db': 1.34,   # ~1.5/1.1
        '6db': 2.00,     # ~2.2/1.1
        '11db': 3.55,    # ~3.9/1.1（取中间值，3.3~3.9V 区间）
    }.get(atten, 3.55)
    vmax_mv = vref * k
    return (raw / 4095.0) * (vmax_mv / 1000.0)

while True:
    raw = read_raw()
    v = raw_to_voltage(raw, vref=1100, atten='11db')
    print("raw=", raw, "V≈", "{:.3f}".format(v))
    time.sleep(0.2)
```

提示：

- 此电压换算为近似值，足够入门；若要提高准确度，参考第 8 节做简易标定。
- 使用 Wi‑Fi 时避免 ADC2 引脚，否则 `adc.read()` 可能失败或返回异常值。

---

## 5. 抗噪与滤波（推荐）

- 多次采样平均：N 次取均值，降低随机噪声，耗时随 N 增加。
- 中值滤波：对尖峰干扰效果好。
- IIR 一阶低通：`y[n]=y[n-1]+α(x[n]-y[n-1])`，平滑且计算轻量。

封装实用工具：

```python
# 文件：adc_util.py
from machine import ADC, Pin

def make_adc(pin_no, atten=ADC.ATTN_11DB, width=None):
    adc = ADC(Pin(pin_no))
    adc.atten(atten)
    if width is not None:
        try:
            adc.width(width)
        except:
            pass
    return adc

def read_raw_12bit(adc):
    try:
        return adc.read()  # 0..4095
    except:
        return adc.read_u16() >> 4

def read_avg(adc, samples=16):
    s = 0
    for _ in range(samples):
        s += read_raw_12bit(adc)
    return s // samples

def read_median(adc, samples=7):
    arr = [read_raw_12bit(adc) for _ in range(samples)]
    arr.sort()
    return arr[len(arr)//2]

class IIR:
    def __init__(self, alpha=0.2, init=None):
        self.a = float(alpha)
        self.y = init

    def step(self, x):
        if self.y is None:
            self.y = float(x)
        else:
            self.y += self.a * (float(x) - self.y)
        return self.y
```

使用（IIR + 均值）：

```python
# 文件：main.py
from machine import ADC, Pin
import time
from adc_util import make_adc, read_avg, IIR

adc = make_adc(34, atten=ADC.ATTN_11DB)
filt = IIR(alpha=0.15)

while True:
    raw = read_avg(adc, samples=32)
    y = filt.step(raw)
    print("raw_avg=", raw, "iir=", int(y))
    time.sleep(0.05)
```

---

## 6. 多通道扫描

轮询多个 ADC1 通道（避免频繁跨 ADC1/ADC2），切换通道后丢弃首读可略减切换误差。

```python
# 文件：main.py
from machine import ADC, Pin
import time

CHS = [32, 33, 34, 35]  # 全部是 ADC1 脚

adcs = []
for p in CHS:
    a = ADC(Pin(p))
    a.atten(ADC.ATTN_11DB)
    try: a.width(ADC.WIDTH_12BIT)
    except: pass
    adcs.append(a)

def read12(a):
    try: return a.read()
    except: return a.read_u16() >> 4

while True:
    vals = []
    for a in adcs:
        _ = read12(a)              # 丢弃一读
        vals.append(read12(a))     # 实读
    print(vals)
    time.sleep(0.1)
```

---

## 7. 定时采样与环形缓冲

周期性采样，主循环批量处理。注意：ESP32 的 Python 级采样频率有限，若需高采样速率应考虑专用外设或 C 扩展。

```python
# 文件：adc_sampler.py
from machine import ADC, Pin, Timer, disable_irq, enable_irq

class Ring:
    def __init__(self, size):
        self.buf = [0]*size
        self.size = size
        self.w = 0
        self.r = 0
    def write(self, v):
        self.buf[self.w] = v
        self.w = (self.w + 1) % self.size
        if self.w == self.r:
            self.r = (self.r + 1) % self.size
    def read_all(self):
        out = []
        while self.r != self.w:
            out.append(self.buf[self.r])
            self.r = (self.r + 1) % self.size
        return out

class ADCSampler:
    def __init__(self, pin_no, period_ms=10, timer_id=0):
        self.adc = ADC(Pin(pin_no))
        self.adc.atten(ADC.ATTN_11DB)
        try: self.adc.width(ADC.WIDTH_12BIT)
        except: pass
        self.ring = Ring(1024)
        self.tim = Timer(timer_id)
    def _read12(self):
        try: return self.adc.read()
        except: return self.adc.read_u16() >> 4
    def _isr(self, _):
        self.ring.write(self._read12())
    def start(self, period_ms=10):
        self.tim.init(period=period_ms, mode=Timer.PERIODIC, callback=self._isr)
    def stop(self):
        self.tim.deinit()
    def fetch(self):
        state = disable_irq()
        data = self.ring.read_all()
        enable_irq(state)
        return data
```

使用：

```python
# 文件：main.py
from adc_sampler import ADCSampler
import time

sam = ADCSampler(pin_no=34, period_ms=5)  # 200Hz
sam.start()
t0 = time.ticks_ms()
for _ in range(20):
    time.sleep_ms(100)
    data = sam.fetch()
    if data:
        avg = sum(data)/len(data)
        print("batch:", len(data), "avg:", int(avg))
print("elapsed:", time.ticks_diff(time.ticks_ms(), t0), "ms")
sam.stop()
```

---

## 8. 电压换算与简易标定

### 8.1 近似换算

设 12 位原始值 `raw ∈ [0,4095]`，参考电压 `Vref≈1.1V`，衰减满量程系数 `k`（见第 4 节）：

- LaTeX：`V_{adc} \approx \frac{raw}{4095} \cdot (k \cdot V_{ref})`

若有分压（R1 上、R2 下）：

- LaTeX：`V_{in} \approx V_{adc} \cdot \frac{R_1 + R_2}{R_2}`

### 8.2 两点线性标定（推荐）

用两个已知电压点（例如 0V 与 3.300V）求线性映射 `V = a*raw + b`：

1. 测 0V：将 ADC 引脚接地，读多次平均得 `raw0`。
2. 测 参考电压：以 3.300V（或用稳压源/USB 3.3V 输出，实测值记为 `Vref_real`），读多次平均得 `raw1`。
3. 计算：
   - LaTeX：`a = \frac{V_{ref\_real} - 0}{raw_1 - raw_0}`, `b = -a \cdot raw_0`
4. 运行时用 `V = a * raw + b` 替代粗略换算。

示例计算代码：

```python
def linear_calibrate(raw0, raw1, v1):
    a = (v1 - 0.0) / (raw1 - raw0)
    b = -a * raw0
    return a, b

# 例：raw0=15（接地残值），raw1=3880（3.300V），得到 a,b 后：
# V = a*raw + b
```

---

## 9. 实战：测量电池/外部电压（分压）

目标：测量 0–12V 电池电压，分压到 0–3.3V。

- 选 `R1=100kΩ, R2=27kΩ`，分压比约 `k_div = (R1+R2)/R2 ≈ 4.7037`
- 预估：12V 经分压后约 2.55V（安全）

代码（带分压与两点标定参数位）：

```python
# 文件：main.py
from machine import ADC, Pin
import time

PIN = 34
R1, R2 = 100000.0, 27000.0
K_DIV = (R1 + R2) / R2

adc = ADC(Pin(PIN))
adc.atten(ADC.ATTN_11DB)
try: adc.width(ADC.WIDTH_12BIT)
except: pass

def read12(a):
    try: return a.read()
    except: return a.read_u16() >> 4

# 如已做线性标定，填入 a,b；否则设为 None 使用近似换算
CAL = None  # (a, b) in volts

def raw_to_vadc(raw):
    if CAL:
        a, b = CAL
        return a*raw + b
    # 近似：按 11dB 量程 3.6~3.9V 中值估算 3.7V
    VFULL = 3.7
    return (raw / 4095.0) * VFULL

while True:
    # 多次平均
    s = 0
    N = 32
    for _ in range(N):
        s += read12(adc)
    raw = s / N
    vadc = raw_to_vadc(raw)       # ADC 芯片端电压
    vin  = vadc * K_DIV           # 分压还原
    print("raw={:.0f} Vadc={:.3f}V  Vin≈{:.3f}V".format(raw, vadc, vin))
    time.sleep(0.5)
```

---

## 10. 常见问题与排查

- 读数乱跳/抖动大：
  - 加 RC 滤波（100nF～1µF 到地），多次采样平均+IIR。
  - 走线尽量短、远离开关电源与电机；参考地良好。
- 电压不准/偏差大：
  - ESP32 ADC 绝对精度差异大，进行两点标定；确认衰减设置正确。
  - 11dB 档在接近满量程区域非线性明显，避免靠近上限；适当降低分压比。
- 一直读不到值或异常：
  - 使用了 ADC2 且 Wi‑Fi 正在工作；改用 ADC1 引脚。
- 读值随通道切换异常：
  - 切换通道后丢弃首读；避免跨 ADC1/ADC2 频繁切换。
- 分压后仍过压：
  - 计算错误或电压超出假定范围；务必先用万用表确认，再上板。

## 11. 小结

本章完成了 ESP32 上 ADC 的基础使用：衰减/量程配置、原始值读取与电压换算；通过多次平均、中值与 IIR 滤波提升稳定度，并实现了多通道扫描与定时采样。针对高于 1.1V 的信号，我们用分压测量并给出了两点线性标定方法，以提升结果的可用性与相对准确度。

---
