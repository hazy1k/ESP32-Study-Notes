# 第十八章 DHT11 湿温度传感器

## 1. 导入

DHT11 是一款单总线（1-Wire 风格，非 Dallas 1-Wire）的数字温湿度传感器，优点是成本低、接线简单；缺点是精度与分辨率较低、采样周期较长（至少 1s 一次）。在 MicroPython 上可直接使用内置 `dht` 模块，快速读取温度与湿度。

- 适用范围与指标（典型）：
  - 温度：0~50°C，精度约 ±2°C
  - 湿度：20~90%RH，精度约 ±5%RH
  - 采样周期：≥1s（建议 2s），比 DHT22 更短（DHT22 ≥2s）

若需要更高精度与更宽量程，建议考虑 DHT22/AM2302（与 DHT11 接口兼容，库同用）。

## 2. 硬件设计

- 供电与电平：
  - VCC 2.7~5.5V，推荐 3.3V 直接供电，逻辑电平与 ESP32 兼容。
- 上拉电阻：
  - 数据线 DQ 需上拉到 VCC（4.7kΩ~10kΩ）。大多数 DHT11 小板已集成上拉电阻与电源指示，无需额外上拉；裸传感器则需自行加上拉。
- 典型接线（以 GPIO4 为例）：

```python
ESP32 3V3  -> DHT11 VCC
ESP32 GND  -> DHT11 GND
ESP32 GPIO4 -> DHT11 DQ（数据）
           |
           +-- 4.7kΩ --→ 3V3（若为裸传感器）
```

- 线长与抗干扰：
  - 线越短越稳（<20~30cm 更佳）；长线请采用屏蔽线、减小上拉阻值（如 4.7kΩ）并降低采样频率。
- 引脚选择：
  - 避免启动相关脚（0/2/15）与 ADC2 受 Wi‑Fi 干扰的场景；常用 GPIO4/5/16/17/18/19/21/22/23/25/26/27/32/33。

## 3. 软件设计

- 核心模块：`dht`（内置），`machine.Pin`，`time`/`uasyncio`
- API（MicroPython）：
  - `dht.DHT11(Pin(...))` 或 `dht.DHT22(Pin(...))`
  - `sensor.measure()`：触发一次采样（阻塞约 10~50ms）
  - `sensor.temperature()`：摄氏度（DHT11 为整数 °C）
  - `sensor.humidity()`：相对湿度 %RH（整数）
- 限频要求：
  - DHT11：两次 `measure()` 间隔≥1s；建议 1.5~2s 稳妥
  - DHT22：间隔≥2s

---

## 4. 快速上手（DHT11）

```python
# 文件：dht_basic.py
from machine import Pin
import dht, time

DHT_PIN = 4

sensor = dht.DHT11(Pin(DHT_PIN))

while True:
    try:
        sensor.measure()
        t = sensor.temperature()   # int, 摄氏度
        h = sensor.humidity()      # int, 相对湿度%
        print("T={}°C, RH={}%" .format(t, h))
    except OSError as e:
        # 时序/接线/干扰可能导致读取失败，建议重试或忽略本次
        print("DHT11 读取失败：", e)
    time.sleep(2)  # 间隔≥1s（建议 2s）
```

提示：

- 刚上电的前几次读取可能失败或不稳定，适当重试与延时。
- 频繁读取会使器件略有自热，适当降低采样频率更稳。

---

## 5. 带重试与限频封装（DHT11/DHT22 通用）

```python
# 文件：dht_reader.py
from machine import Pin
import dht, time

class DHTReader:
    """
    统一封装 DHT11/DHT22：
    - 限制最小读取间隔（防止采样过快）
    - 失败重试（短延时）
    - 保留最后一次成功值（可选返回）
    """
    def __init__(self, pin_no, model="DHT11", min_interval_ms=None):
        self.pin = Pin(pin_no)
        if model.upper() == "DHT22":
            self.sensor = dht.DHT22(self.pin)
            self.min_interval = int(min_interval_ms or 2000)
        else:
            self.sensor = dht.DHT11(self.pin)
            self.min_interval = int(min_interval_ms or 1100)
        self._last_ms = 0
        self._last = None   # (t, h)

    def read(self, retries=2, retry_delay_ms=50, fallback_last=False):
        """
        返回 (t, h)，单位 (°C, %RH)，失败抛 OSError
        - fallback_last=True 时失败则返回上次值或抛异常（若无历史）
        """
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_ms) < self.min_interval:
            # 未到最小间隔：直接返回上次值或等待后再读
            if self._last is not None:
                return self._last
            # 无历史则等待到间隔到期
            time.sleep_ms(self.min_interval - time.ticks_diff(now, self._last_ms))

        err = None
        for _ in range(max(1, retries + 1)):
            try:
                self.sensor.measure()
                t = self.sensor.temperature()
                h = self.sensor.humidity()
                # 规范成 float 便于后续处理
                t = float(t)
                h = float(h)
                self._last = (t, h)
                self._last_ms = time.ticks_ms()
                return self._last
            except OSError as e:
                err = e
                time.sleep_ms(retry_delay_ms)
        if fallback_last and self._last is not None:
            return self._last
        raise err or OSError("DHT 读取失败")

if __name__ == "__main__":
    rdr = DHTReader(pin_no=4, model="DHT11")
    while True:
        try:
            t, h = rdr.read(retries=2, fallback_last=True)
            print("T={:.1f}°C RH={:.0f}%".format(t, h))
        except OSError as e:
            print("读取失败：", e)
        time.sleep(2)
```

---

## 6. uasyncio 异步采集

```python
# 文件：dht_async.py
from machine import Pin
import dht
import uasyncio as asyncio
import time

class DHTTask:
    def __init__(self, pin_no, model="DHT11", period_ms=2000):
        self.sensor = dht.DHT11(Pin(pin_no)) if model.upper()=="DHT11" else dht.DHT22(Pin(pin_no))
        self.period = int(period_ms)
        self.latest = None     # (t, h)
        self.last_ok_ms = 0

    async def run(self):
        while True:
            try:
                self.sensor.measure()
                t = float(self.sensor.temperature())
                h = float(self.sensor.humidity())
                self.latest = (t, h)
                self.last_ok_ms = time.ticks_ms()
                # print("T={:.1f} RH={:.0f}%".format(t, h))
            except OSError:
                pass
            await asyncio.sleep_ms(self.period)

async def main():
    task = DHTTask(pin_no=4, model="DHT11", period_ms=2000)
    asyncio.create_task(task.run())
    while True:
        if task.latest:
            t, h = task.latest
            print("T={:.1f} RH={:.0f}% (age={}ms)".format(t, h, time.ticks_diff(time.ticks_ms(), task.last_ok_ms)))
        await asyncio.sleep(1)

asyncio.run(main())
```

---

## 7. 进阶：露点/绝对湿度/体感温度

给出常用空气参数换算，便于环境监测展示与告警。

- 露点温度（Magnus 公式，T 以 °C，RH=0..100）：
  
  - 设 `a=17.27, b=237.7`
  - LaTeX：`\gamma(T, RH)=\ln(RH/100)+\frac{a T}{b+T}`
  - LaTeX：`T_{dew}=\frac{b\cdot \gamma}{a-\gamma}`

- 绝对湿度 AH（g/m³，近似）：
  
  - 饱和蒸汽压（hPa）：LaTeX：`e_s=6.112\exp\left(\frac{17.67T}{T+243.5}\right)`
  - 实际蒸汽压：LaTeX：`e=RH/100\cdot e_s`
  - 绝对湿度：LaTeX：`AH=\frac{2.1674\cdot e}{273.15+T}\cdot 100`（单位换算）

- 简化体感温度（Heat Index，华氏下经验式，以下给出摄氏近似）：

```python
# 文件：env_calc.py
import math

def dew_point_c(t_c, rh):
    a, b = 17.27, 237.7
    gamma = math.log(max(1e-6, rh/100.0)) + (a*t_c)/(b + t_c)
    return (b*gamma) / (a - gamma)

def abs_humidity_gm3(t_c, rh):
    es = 6.112 * math.exp((17.67 * t_c) / (t_c + 243.5))  # hPa
    e  = (rh/100.0) * es
    ah = (2.1674 * e) / (273.15 + t_c) * 100.0
    return ah

def heat_index_c(t_c, rh):
    # 简化近似（T 26~50°C, RH 40~100% 区间），低温低湿下返回原温度
    t_f = t_c * 9/5 + 32
    hi_f = (-42.379 + 2.04901523*t_f + 10.14333127*rh
            - 0.22475541*t_f*rh - 6.83783e-3*t_f*t_f
            - 5.481717e-2*rh*rh + 1.22874e-3*t_f*t_f*rh
            + 8.5282e-4*t_f*rh*rh - 1.99e-6*t_f*t_f*rh*rh)
    hi_c = (hi_f - 32) * 5/9
    if t_c < 26 or rh < 40:
        return t_c
    return hi_c

if __name__ == "__main__":
    t, h = 30.0, 70.0
    print("dew={:.1f}°C, AH={:.1f} g/m³, HI={:.1f}°C".format(
        dew_point_c(t,h), abs_humidity_gm3(t,h), heat_index_c(t,h)))
```

---

## 8. 与深度睡眠配合（超低功耗）

```python
# 文件：dht_deepsleep.py
from machine import Pin, deepsleep
import dht, time

sensor = dht.DHT11(Pin(4))
try:
    sensor.measure()
    t = sensor.temperature()
    h = sensor.humidity()
    print("T={} RH={}".format(t, h))
except OSError as e:
    print("read err:", e)

# 休眠 60s 后唤醒重新测量
deepsleep(60_000)
```

注意：唤醒后程序从头开始执行，若需要带时间戳记录，可结合上一章 RTC/NTP。

---

## 9. 常见问题与排查

- 读取失败/抛 OSError：
  - 线过长/干扰强；减少线长、优化走线与上拉阻值。
  - 上拉缺失（裸芯片）；补 4.7kΩ~10kΩ 到 VCC。
  - 采样过快；确保两次 `measure()` 间隔≥1s（DHT22 ≥2s）。
  - 使用了不合适的 GPIO（启动脚/受占用）；换常规 GPIO。
- 值明显不准/跳变大：
  - 器件精度较低；远离热源与风口，降低采样频率减少自热，必要时使用软件平滑（IIR/移动平均）。
  - 与标准温湿度计比对后做软件偏移校正。
- 仅温度有变化，湿度常 20%/90%：
  - DHT11 分辨率与精度有限，湿度边界容易钉死；确认环境或更换 DHT22。
- 上电首次读到异常值：
  - 正常现象；上电等待 1~2s 或忽略首次结果。

---

## 10. 小结

本章介绍了 DHT11 的硬件接线要点（数据上拉、线长与供电）、MicroPython 内置 `dht` 模块的基础用法，并给出了带“最小间隔+重试+历史回退”的通用封装与 uasyncio 异步采集。还提供了露点、绝对湿度与体感温度的常用环境量计算。若对精度/量程有更高要求，建议平滑迁移到 DHT22，API 与本章完全兼容，仅需调整最小采样间隔。

---
