# 第七章 步进电机

## 1. 导入

步进电机通过“脉冲计数”实现精准角度与位移控制，与直流电机（靠闭环调速）不同，步进电机“给多少步走多少步”。常见两类接法：

- 28BYJ-48 + ULN2003（5 线单极性，减速齿轮，低速、力矩小、便宜易用）
- NEMA17 等双极性步进电机 + A4988/DRV8825/TMC 系列驱动（STEP/DIR 接口，可微步，高速、力矩大）

本章分别给出两类电机的接线与代码，涵盖速度/方向控制、微步设置、释放/抱闸、加减速斜坡，以及协程非阻塞驱动。

## 2. 硬件设计

- 电源与地线：
  - 电机电源与 ESP32 逻辑电源建议分开供电，但 GND 必须共地。
  - 不要用 ESP32 的 3.3V/5V 口直接给电机供电。电机瞬时电流大，需要独立稳压电源。
- 干扰与去耦：
  - 电机是强干扰源；在驱动板和电源端加 100µF 电解 + 0.1µF 陶瓷去耦；线尽量短、星形接地。
- 安全 GPIO：
  - 避免使用启动相关脚 GPIO0/GPIO2/GPIO15；优先 4/5/16/17/18/19/21/22/23/25/26/27/32/33。

### 2.1 28BYJ-48 + ULN2003

- 供电：通常 5V（也有 12V 版，按铭牌），请接到电机电源，勿接 ESP32 3.3V。
- 接线（示例）：

```c
ULN2003 IN1..IN4 --> ESP32 GPIO(14, 27, 26, 25)   // 仅信号
ULN2003 VCC      --> 外部 5V
ULN2003 GND      --> GND（与 ESP32 共地）
电机五芯线        --> 插在 ULN2003 插座（方向正确）
```

电机五芯线 --> 插在 ULN2003 插座（方向正确）

- 步距与齿比：
  - 28BYJ-48 内部步距 11.25°（32 步/圈），带约 1:64 齿轮。常见库设“每圈步数”为 2048（全步）或 4096（半步），实际略有误差。
  - 建议将 `steps_per_rev` 做成参数，后续标定。

### 2.2 NEMA17 + A4988/DRV8825（STEP/DIR）

- 供电：VMOT（电机电源，如 12V），VDD（逻辑 3.3/5V）。
- 接线（示例，A4988）：

```c
ESP32 GPIO25 -> STEP     （脉冲上升沿触发，>1us）
ESP32 GPIO26 -> DIR      （方向 0/1）
ESP32 GPIO27 -> ENABLE   （低有效，拉低使能，可省略）
ESP32 GPIO21 -> MS1      （微步选择，可省略）
ESP32 GPIO22 -> MS2
ESP32 GPIO23 -> MS3
A4988 VDD    -> 3.3V（逻辑）
A4988 GND    -> GND（与 ESP32 共地）
A4988 VMOT   -> 12V 电机电源（旁路电容靠近驱动）
A4988 2A/2B/1A/1B -> 步进电机两相
```

- 注意事项：
  - 调 Vref 限流以保护电机与驱动（依驱动与电机相电流计算）。
  - 脉冲最小高电平宽度：A4988 ≥1µs（DRV8825 ≥1.9µs）；步频过高会丢步。
  - 微步设置：MS1/MS2/MS3 组合对应 1/2/4/8/16（DRV8825 可到 32）。

## 3. 软件设计

### 3.1 实验目标

- 28BYJ：全步/半步/波动三种激励，指定角度/圈数移动，释放/抱闸。
- STEP/DIR：方向、微步、转速控制；实现加减速斜坡（减小丢步）。
- 支持阻塞与 uasyncio 协程（非阻塞）两种方式。

### 3.2 关键模块

- `machine.Pin`：GPIO 输出（相位/STEP/DIR/EN/MS1..3）
- `time`：`ticks_us`/`sleep_us` 精确脉冲与步间隔
- `uasyncio`：并发与非阻塞时序

---

## 4. 28BYJ-48：相位序列驱动

### 4.1 封装：Stepper28BYJ（ULN2003）

```python
# 文件：stepper28.py
from machine import Pin
import time

# 三种常用相位序列（按 IN1,IN2,IN3,IN4）
SEQ_WAVE = [
    (1,0,0,0),
    (0,1,0,0),
    (0,0,1,0),
    (0,0,0,1),
]
SEQ_FULL = [
    (1,1,0,0),
    (0,1,1,0),
    (0,0,1,1),
    (1,0,0,1),
]
SEQ_HALF = [
    (1,0,0,0),
    (1,1,0,0),
    (0,1,0,0),
    (0,1,1,0),
    (0,0,1,0),
    (0,0,1,1),
    (0,0,0,1),
    (1,0,0,1),
]

class Stepper28BYJ:
    def __init__(self, pins, mode="half", steps_per_rev=4096):
        """
        pins: [IN1, IN2, IN3, IN4]（与 ULN2003 IN1..IN4 对应）
        mode: "wave"|"full"|"half"（半步推荐，细腻力矩均衡）
        steps_per_rev: 配合所选模式的“每圈步数”，默认 4096（常用半步）
        """
        self.pins = [Pin(p, Pin.OUT, value=0) for p in pins]
        self.mode = None
        self.seq = None
        self.set_mode(mode)
        self.steps_per_rev = steps_per_rev
        self._idx = 0

    def set_mode(self, mode):
        if mode == self.mode:
            return
        if mode == "wave":
            self.seq = SEQ_WAVE
        elif mode == "full":
            self.seq = SEQ_FULL
        elif mode == "half":
            self.seq = SEQ_HALF
        else:
            raise ValueError("mode 必须为 wave/full/half")
        self.mode = mode
        self._idx = 0

    def _apply(self, state):
        for pin, v in zip(self.pins, state):
            pin.value(v)

    def release(self):
        """释放线圈（省电、无保持力矩）"""
        for pin in self.pins:
            pin.value(0)

    def hold(self):
        """保持当前相位（有保持力矩、发热）"""
        self._apply(self.seq[self._idx])

    def step_once(self, direction=1):
        """单步：direction=+1 正向，-1 反向"""
        n = len(self.seq)
        self._idx = (self._idx + direction) % n
        self._apply(self.seq[self._idx])

    def move_steps(self, steps, rpm=10):
        """
        以给定 rpm（转/分）移动 steps 步（可正可负，负值反转）。
        """
        if steps == 0:
            return
        direction = 1 if steps > 0 else -1
        steps = abs(steps)
        # 单步间隔（微秒）：60 秒 / (rpm * steps_per_rev) -> 秒/步
        delay_us = int(60_000_000 / (rpm * self.steps_per_rev))
        delay_us = max(800, delay_us)  # 过快易丢步，保守下限
        for _ in range(steps):
            self.step_once(direction)
            time.sleep_us(delay_us)

    def move_deg(self, deg, rpm=10):
        """按角度移动（正=顺时针/取决于接线），deg 可负"""
        steps = int(self.steps_per_rev * (deg / 360.0))
        self.move_steps(steps, rpm=rpm)
```

### 4.2 示例：旋转 90°、一圈、释放

```python
# 文件：main.py
from stepper28 import Stepper28BYJ

MOTOR_PINS = [14, 27, 26, 25]     # IN1..IN4
motor = Stepper28BYJ(MOTOR_PINS, mode="half", steps_per_rev=4096)

# 旋转 90 度（顺时针）
motor.move_deg(90, rpm=12)
# 反向 90 度
motor.move_deg(-90, rpm=12)
# 一整圈
motor.move_steps(4096, rpm=10)

# 释放线圈（省电）
motor.release()
```

- 若发现角度累计误差，校准 `steps_per_rev`（例如 4076~4096）。
- 需要保持位置抗干扰，请用 `hold()` 维持上一次相位（注意发热）。

---

## 5. STEP/DIR：A4988/DRV8825 驱动

### 5.1 封装：StepDir（微步、速度、斜坡）

```python
# 文件：stepdir.py
from machine import Pin
import time
try:
    import uasyncio as asyncio
except ImportError:
    asyncio = None

_MICROSTEP_TABLE = {
    1:  (0,0,0),
    2:  (1,0,0),
    4:  (0,1,0),
    8:  (1,1,0),
    16: (1,1,1),
    # DRV8825 可到 32： (1,0,1) 等，视芯片而定
}

class StepDir:
    def __init__(self, step, dir, en=None, ms1=None, ms2=None, ms3=None,
                 steps_per_rev=200, driver="A4988"):
        """
        step/dir/en/ms1..3: 对应引脚号（可为 None）
        steps_per_rev: 电机基础全步步数（NEMA17 多为 200）
        driver: 影响最小脉宽等注释（A4988/DRV8825）
        """
        self.step = Pin(step, Pin.OUT, value=0)
        self.dir  = Pin(dir,  Pin.OUT, value=0)
        self.en   = Pin(en,   Pin.OUT, value=1) if en is not None else None
        self.ms1  = Pin(ms1,  Pin.OUT, value=0) if ms1 is not None else None
        self.ms2  = Pin(ms2,  Pin.OUT, value=0) if ms2 is not None else None
        self.ms3  = Pin(ms3,  Pin.OUT, value=0) if ms3 is not None else None

        self.driver = driver
        self.base_steps = steps_per_rev
        self.microstep = 1  # 当前微步倍率
        self.set_microstep(1)  # 默认全步

        # 经验下限：保证脉冲宽度与间隔
        self.min_pulse_us = 2 if driver.upper()=="A4988" else 3
        self.min_step_interval_us = 200  # 5kHz 上限，视系统而定

    def set_enable(self, enabled=True):
        if self.en is None:
            return
        # A4988/DRV8825 ENABLE 为低有效
        self.en.value(0 if enabled else 1)

    def set_dir(self, forward=True):
        self.dir.value(1 if forward else 0)

    def set_microstep(self, m=1):
        m = int(m)
        if self.ms1 is None or self.ms2 is None or self.ms3 is None:
            # 无 MS 引脚时，只在内部记录倍率
            self.microstep = m
            return
        if m not in _MICROSTEP_TABLE:
            raise ValueError("不支持的微步倍率：{}".format(m))
        s1, s2, s3 = _MICROSTEP_TABLE[m]
        self.ms1.value(s1); self.ms2.value(s2); self.ms3.value(s3)
        self.microstep = m

    def _pulse(self, pulse_us=None):
        """产生一个 STEP 脉冲（上升沿有效），宽度 >= min_pulse_us"""
        w = max(self.min_pulse_us, int(pulse_us or self.min_pulse_us))
        self.step.value(1)
        time.sleep_us(w)
        self.step.value(0)

    def effective_steps_per_rev(self):
        return self.base_steps * self.microstep

    def move_steps(self, steps, rpm=60):
        """
        阻塞移动给定步数（可负），rpm 为机械转速（电机轴，非“步/秒”）
        """
        if steps == 0:
            return
        forward = steps > 0
        self.set_dir(forward)
        steps = abs(steps)

        eff_steps = self.effective_steps_per_rev()
        interval_us = int(60_000_000 / (rpm * eff_steps))  # 步间隔
        interval_us = max(interval_us, self.min_step_interval_us)

        self.set_enable(True)
        for _ in range(steps):
            self._pulse()
            time.sleep_us(interval_us)
        self.set_enable(False)

    def move_trapezoid(self, steps, vmax_sps=1200, ramp_steps=200):
        """
        简化三角/梯形速度曲线（以 步/秒 为单位）：
        - 从低速线性加速到 vmax_sps，再匀速（若有），再减速到 0
        - ramp_steps: 加速段步数（减速对称），总步数不足时自动缩短到三角形
        """
        if steps == 0:
            return
        forward = steps > 0
        self.set_dir(forward)
        steps = abs(steps)

        up = min(ramp_steps, steps // 2)
        flat = steps - 2 * up

        def delay_from_sps(sps):
            sps = max(1, int(sps))
            return max(self.min_step_interval_us, int(1_000_000 / sps))

        self.set_enable(True)
        # 加速
        for i in range(up):
            sps = max(200, int(vmax_sps * (i + 1) / up))  # 从 ~200sps 起步
            self._pulse()
            time.sleep_us(delay_from_sps(sps))
        # 匀速
        for _ in range(flat):
            self._pulse()
            time.sleep_us(delay_from_sps(vmax_sps))
        # 减速
        for i in range(up, 0, -1):
            sps = max(200, int(vmax_sps * i / up))
            self._pulse()
            time.sleep_us(delay_from_sps(sps))
        self.set_enable(False)

    async def move_steps_async(self, steps, rpm=60):
        if asyncio is None:
            raise RuntimeError("uasyncio 不可用")
        if steps == 0:
            return
        forward = steps > 0
        self.set_dir(forward)
        steps = abs(steps)

        eff_steps = self.effective_steps_per_rev()
        interval_us = int(60_000_000 / (rpm * eff_steps))
        interval_us = max(interval_us, self.min_step_interval_us)

        self.set_enable(True)
        for _ in range(steps):
            self._pulse()
            # asyncio 对 us 级别不精确，这里用 ms 近似
            await asyncio.sleep_ms(max(1, interval_us // 1000))
        self.set_enable(False)
```

### 5.2 示例：一圈、微步、斜坡

```python
# 文件：main.py
from stepdir import StepDir
import time

# A4988 引脚（按你的接线修改）
STEP, DIR, EN = 25, 26, 27
MS1, MS2, MS3 = 21, 22, 23

drv = StepDir(step=STEP, dir=DIR, en=EN, ms1=MS1, ms2=MS2, ms3=MS3, steps_per_rev=200)

# 全步，60rpm 转一圈
drv.set_microstep(1)
drv.move_steps(steps=drv.effective_steps_per_rev(), rpm=60)
time.sleep(0.5)

# 1/16 微步，30rpm 转半圈
drv.set_microstep(16)
half_rev = drv.effective_steps_per_rev() // 2
drv.move_steps(steps=half_rev, rpm=30)
time.sleep(0.5)

# 梯形加减速移动 2000 步，峰值 1500 步/秒，ramp 300 步
drv.move_trapezoid(steps=2000, vmax_sps=1500, ramp_steps=300)
```

---

## 6. 协程版演示（非阻塞）

与其他任务并行运行（如传感器/网络）。注意：MicroPython 的协程定时精度以 ms 计，适合低至中低步频（~几百 sps）。

```python
# 文件：main_async.py
from stepdir import StepDir
import uasyncio as asyncio

STEP, DIR, EN = 25, 26, 27
MS1, MS2, MS3 = 21, 22, 23

async def main():
    drv = StepDir(STEP, DIR, EN, MS1, MS2, MS3, steps_per_rev=200)
    drv.set_microstep(8)
    # 并行两个任务：循环转动 + 打印状态
    async def spin():
        while True:
            await drv.move_steps_async(drv.effective_steps_per_rev()//4, rpm=20)
            await asyncio.sleep(0.3)
            await drv.move_steps_async(-drv.effective_steps_per_rev()//4, rpm=20)
            await asyncio.sleep(0.3)
    async def status():
        while True:
            print("running...")
            await asyncio.sleep(1)
    await asyncio.gather(spin(), status())

asyncio.run(main())
```

---

## 7. 工程建议与参数选择

- 步频与丢步：
  - 低速大力矩，高速力矩下降；起步步频过高易丢步，使用加速斜坡改善。
  - 典型稳妥步频：几百到 1~2 kHz；更高需优化代码或用专用定时/RMT 外设。
- 微步与力矩：
  - 微步让运行更平滑，但单微步力矩下降；负载重时可降低微步或提高电流限流。
- 28BYJ 标定：
  - 以 4096（半步）或 2048（全步）起步，实机测试 10 圈，修正 `steps_per_rev`。
- A4988/DRV8825：
  - 设置 Vref（限流）匹配电机额定相电流；加散热片/风冷避免过热。
  - STEP 脉冲高电平 ≥1µs（DRV8825 ≥1.9µs），步间隔满足数据手册。
- 释放与发热：
  - 停机时释放线圈可降温省电；需要抗扰保持位置则保持上电，但注意温升。
- 限位与归零：
  - 工程上加限位开关（光电/机械），上电先归零；可用 `Pin.IRQ` 捕获限位信号并停步。

## 8. 常见问题与排查

- 抖动、不转或异响：
  - 线序错或相序不对（28BYJ IN1..IN4 顺序错误）；A4988 电机两相接错。
- 丢步/失步：
  - 起步速度过高、加速度过快、供电电压偏低、负载过大；增加 ramp，降速或升压（在额定范围内）。
- 过热：
  - 电流限流过大或持续抱闸；调低 Vref，空闲释放线圈。
- 高速尖叫：
  - 微步更细、高频 PWM（TMC 系列更安静）、机械减振。
- 角度误差积累（28BYJ）：
  - 齿比非整（~1:63.684），累积误差需软件标定或闭环校正。

## 9. 小结

本章分别实现了 28BYJ-48（ULN2003 相位序列）与 NEMA17（A4988/DRV8825 STEP/DIR）的控制：完成方向/速度/角度控制、微步设置、释放/抱闸，并给出了简化的梯形加减速与协程非阻塞示例。通过合理的电源、接线与时序参数，你可以在 ESP32 上稳定地驱动步进电机完成定位与运动任务。

---
