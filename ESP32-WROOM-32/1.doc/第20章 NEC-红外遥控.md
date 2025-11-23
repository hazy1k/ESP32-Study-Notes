# 第二十章 红外遥控（IR Remote）

## 1. 导入

红外遥控广泛用于家电控制。典型方案是用 38kHz 载波调制的编码协议（最常见为 NEC），接收端使用带解调的红外接收头（如 VS1838B/TSOP38238），输出为“低电平脉冲序列”。ESP32 上可用两种方式实现：

- 基于 `time_pulse_us` 的时序测量：简单稳妥，足够应对 NEC。
- 基于 RMT 外设（`esp32.RMT`）：硬件捕获/发射脉冲，更抗抖且便于发码。

本章给出硬件接线、安全驱动、NEC 协议解码与发码的完整 MicroPython 代码，并说明按键“长按重复”处理与常见问题排查。

## 2. 硬件设计

- 红外接收头（解调型）：
  - 典型型号：VS1838B、TSOP38238（38kHz）。
  - 引脚：`VCC(3.3V/5V)`, `GND`, `OUT`（空闲高电平，收到“载波标记”时输出低电平脉冲）。
  - 供电建议 3.3V，部分模块支持 5V，但请与 ESP32 共地。
- 红外发射（IR LED）：
  - IR LED 需较大瞬时电流，用 NPN 三极管驱动，GPIO 仅驱动三极管基极。
  - 参考连接（以 GPIO25 为例）：

```c
ESP32 GPIO25 --1kΩ--> NPN(B)
NPN(E) ---------------- GND
NPN(C) -- IR LED(极性正确) -- 100Ω -- +3.3V
（收发共地，发射端建议近端再并 100nF 去耦）
```

- 引脚选择：
  - 接收 `OUT` 接任意可用输入脚（如 34/35/36/39 也可，仅输入）。
  - 发射 GPIO 需支持普通输出（并尽量避开板载冲突脚），如 25/26/27 等。

提示：本章默认协议为 NEC（38kHz，广泛使用于电视/空调/机顶盒等）。

## 3. 协议速览（NEC）

- 物理层：38kHz 载波，接收头输出为“低电平＝有载波（mark）”，高电平＝无载波（space）。
- 帧结构（NEC 标准帧 32bit，LSB first）：
  - 引导：9ms mark + 4.5ms space
  - 数据：32 位（8bit 地址 + 8bit 地址反码 + 8bit 命令 + 8bit 命令反码），每位为 560us mark +（0位：560us space；1位：1690us space）
  - 结尾：560us mark
- 重复帧（长按）：9ms mark + 2.25ms space + 560us mark（不含 32bit 数据）

容差：各时间值允许约 ±20% 误差（不同遥控器会有漂移）。

---

## 4. NEC 接收（`time_pulse_us` 方案，通用稳定）

无需 RMT，直接用 `time_pulse_us` 串行测量脉冲长度，可靠解码 NEC。

```python
# 文件：nec_recv.py
from machine import Pin, time_pulse_us
import time

class NECReceiver:
    """
    基于 time_pulse_us 的 NEC 解码器
    - 返回 (addr, cmd, repeat)，repeat=True 表示重复帧（长按）
    - addr/cmd 为 0..255 的 int；repeat 帧仅指示“重复”，不含数据
    """
    def __init__(self, rx_pin):
        self.pin = Pin(rx_pin, Pin.IN)
        self.last_addr = None
        self.last_cmd = None

    @staticmethod
    def _in_range(x, lo, hi):
        return lo <= x <= hi

    def _read_mark(self, expected_us, tol=0.25, timeout=20000):
        t = time_pulse_us(self.pin, 0, timeout)  # mark=低
        if t < 0:
            return None
        return t if self._in_range(t, expected_us*(1-tol), expected_us*(1+tol)) else None

    def _read_space(self, expected_us, tol=0.25, timeout=20000):
        t = time_pulse_us(self.pin, 1, timeout)  # space=高
        if t < 0:
            return None
        return t if self._in_range(t, expected_us*(1-tol), expected_us*(1+tol)) else None

    def read(self, timeout_ms=200):
        """
        试图读取一帧，成功返回 (addr, cmd, repeat)，失败返回 None
        """
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
            # 1) 等待引导 9ms mark
            t_mark = time_pulse_us(self.pin, 0, 20000)
            if t_mark < 0:
                continue
            if not self._in_range(t_mark, 9000*0.8, 9000*1.2):
                # 不是 NEC 引导，继续找
                continue

            # 2) 引导后的 space：4.5ms(正常) 或 2.25ms(重复帧)
            t_space = time_pulse_us(self.pin, 1, 10000)
            if t_space < 0:
                continue

            if self._in_range(t_space, 4500*0.8, 4500*1.2):
                # 正常帧：读取 32bit
                data = 0
                for i in range(32):
                    # 560us mark
                    t = time_pulse_us(self.pin, 0, 2000)
                    if t < 0 or not self._in_range(t, 560*0.6, 560*1.4):
                        return None
                    # space：0->约560us，1->约1690us
                    t = time_pulse_us(self.pin, 1, 3000)
                    if t < 0:
                        return None
                    bit = 1 if t > 1120 else 0
                    data |= (bit << i)

                # 尾部 560us mark（可读可不读）
                try:
                    time_pulse_us(self.pin, 0, 2000)
                except:
                    pass

                addr     = (data >> 0)  & 0xFF
                addr_inv = (data >> 8)  & 0xFF
                cmd      = (data >> 16) & 0xFF
                cmd_inv  = (data >> 24) & 0xFF

                if (addr ^ addr_inv) != 0xFF or (cmd ^ cmd_inv) != 0xFF:
                    return None

                self.last_addr, self.last_cmd = addr, cmd
                return (addr, cmd, False)

            elif self._in_range(t_space, 2250*0.8, 2250*1.2):
                # 重复帧（长按）
                # 读掉最后 560us mark
                try:
                    time_pulse_us(self.pin, 0, 2000)
                except:
                    pass
                return (self.last_addr, self.last_cmd, True)

            else:
                # 非 NEC 帧
                continue

        return None

if __name__ == "__main__":
    rx = NECReceiver(rx_pin=23)  # 按你的接线修改
    print("等待红外按键...")
    hold = False
    while True:
        r = rx.read(timeout_ms=300)
        if r is None:
            continue
        addr, cmd, rep = r
        if addr is None:
            # 尚无历史，忽略重复帧
            continue
        if rep:
            if not hold:
                print("重复：addr=0x%02X cmd=0x%02X" % (addr, cmd))
                hold = True
        else:
            print("按键：addr=0x%02X cmd=0x%02X" % (addr, cmd))
            hold = False
```

说明：

- `time_pulse_us` 忙等测时，适合 NEC（单帧 < 100ms）；若需后台并发，见第 7 节的协程封装。
- `repeat=True` 表示长按重复；数据沿用上一次完整帧的 `addr/cmd`。

---

## 5. NEC 发射（RMT 方案，38kHz 载波）

ESP32 的 RMT 硬件可边沿精确输出“载波开/关”的脉冲序列，发码稳定可靠。

```python
# 文件：ir_tx_nec.py
from machine import Pin
from esp32 import RMT

class NECTx:
    """
    使用 RMT 发射 NEC 码（38kHz, 1/3 占空）
    """
    def __init__(self, tx_pin, channel=0, carrier_khz=38, duty_percent=33):
        self.rmt = RMT(channel, pin=Pin(tx_pin), clock_div=80)  # 1us 分辨率
        self.rmt.tx_carrier(carrier_khz*1000, duty_percent)

    @staticmethod
    def _frame_pulses(addr, cmd):
        """
        生成 NEC 脉冲序列（单位 us），序列按 [mark, space, mark, space, ...]
        """
        def bit_pulses(b):
            # 1bit：560 mark + (0:560 space / 1:1690 space)
            return [560, 560 if b == 0 else 1690]

        # 32bit: addr, ~addr, cmd, ~cmd （均 LSB first）
        a  = addr & 0xFF
        na = a ^ 0xFF
        c  = cmd & 0xFF
        nc = c ^ 0xFF
        bits = []
        for byte in (a, na, c, nc):
            for i in range(8):
                bits.append((byte >> i) & 1)

        pulses = [9000, 4500]  # 引导
        for b in bits:
            pulses += bit_pulses(b)
        pulses += [560]         # 结尾 mark
        return pulses

    @staticmethod
    def _repeat_pulses():
        # 重复帧
        return [9000, 2250, 560]

    def send(self, addr, cmd, repeats=0, repeat_gap_ms=110):
        # 先发一次完整帧
        pulses = self._frame_pulses(addr, cmd)
        self.rmt.write_pulses(pulses, start=1)  # start=1 表示先输出“mark段”（含载波）
        if repeats > 0:
            import time
            for _ in range(repeats):
                time.sleep_ms(repeat_gap_ms)
                self.rmt.write_pulses(self._repeat_pulses(), start=1)

if __name__ == "__main__":
    tx = NECTx(tx_pin=25)  # 修改为你的发射脚
    # 例：发送地址 0x00、命令 0x45（不同遥控器映射不同）
    tx.send(addr=0x00, cmd=0x45, repeats=2)
    print("NEC 已发送")
```

说明：

- 上述代码使用 `esp32.RMT`，若你的固件还在旧接口，可能需要微调方法名；多数近年版本保持一致。
- `repeats` 用于模拟“长按”，一般每 110ms 发送一次重复帧。
- 发射端一定要用三极管驱动 IR LED，不要让 GPIO 直推大电流。

---

## 6. 键映射与动作绑定（示例）

将遥控器按键映射到具体动作，支持长按重复。

```python
# 文件：ir_actions.py
from nec_recv import NECReceiver
from machine import Pin
import time

# 示例：用板载 LED 指示（替换为你自己的业务逻辑）
LED = Pin(2, Pin.OUT)

ACTIONS = {
    # addr 可用通配（多数遥控 addr=0x00/0xFF），实际请用打印值确认
    (0x00, 0x45): "TOGGLE_LED",
    (0x00, 0x46): "LED_ON",
    (0x00, 0x47): "LED_OFF",
}

def do_action(act, repeat):
    if act == "TOGGLE_LED" and not repeat:
        LED.value(1 - LED.value())
    elif act == "LED_ON":
        LED.value(1)
    elif act == "LED_OFF":
        LED.value(0)

if __name__ == "__main__":
    rx = NECReceiver(rx_pin=23)
    print("等待遥控器...")
    while True:
        r = rx.read(timeout_ms=300)
        if r is None:
            continue
        addr, cmd, rep = r
        if addr is None:
            continue
        act = ACTIONS.get((addr, cmd))
        if act:
            do_action(act, rep)
        else:
            # 未绑定的键，打印学习
            print("unknown: addr=0x%02X cmd=0x%02X rep=%s" % (addr, cmd, rep))
```

---

## 7. 协程轮询（非阻塞主循环）

`time_pulse_us` 为忙等，单次解码会短暂占用 CPU。若你使用 `uasyncio`，可用“小步轮询 + 短超时”的方式减轻对其他任务的影响：

```python
# 文件：ir_async.py
from nec_recv import NECReceiver
import uasyncio as asyncio

async def ir_task(rx: NECReceiver):
    while True:
        r = rx.read(timeout_ms=50)  # 短超时，避免长时阻塞
        if r:
            addr, cmd, rep = r
            if addr is not None:
                print("IR:", hex(addr), hex(cmd), "rep" if rep else "")
        await asyncio.sleep_ms(10)   # 给其他任务让路

async def main():
    rx = NECReceiver(rx_pin=23)
    asyncio.create_task(ir_task(rx))
    # 你的其他任务...
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
```

---

## 8. 进阶：RC5 协议（概览）

- RC5 采用双相（曼彻斯特）编码，单位时间 T≈889us，逻辑位通过电平在中点翻转体现。
- 帧包含起始位、切换位（每次按键改变 0/1 以区分短/长按）、地址与命令。
- 解码思路：
  - 用 RMT 捕获电平持续时间序列，按 T 或 2T 将序列归一化，再依据“中点翻转”恢复位流。
  - 本章不展开完整 RC5 解码实现；若仅需 NEC，建议专注 NEC 以降低复杂度。

---

## 9. 常见问题与排查

- 接收不稳定/解码失败：
  - 不是 NEC 协议（例如 RC5/SONY）；请换解码器或先做“原始脉冲打印”确认。
  - 接收头供电不稳/共地不良；加近端 100nF，缩短线。
  - 光照强烈（阳光、白炽灯）可能干扰，尽量避开直射。
- 长按无反应：
  - 忘记处理 NEC 重复帧；见代码里 `repeat=True` 的情况。
- 发射没反应：
  - IR LED 没用三极管放大；电流太小距离短。检查极性、限流、电源。
  - 载波频率不对（多数接收头是 38kHz）；`tx_carrier(38000, 33%)` 较通用。
  - 波形脉冲时序错误；对照示波器或缩小容差。
- 不同遥控器地址不同：
  - 同品牌也可能不同 `addr`，请先用接收程序打印学习再映射。
- RMT API 差异：
  - 若 `esp32.RMT` 方法名略有不同（历史固件），可参考固件文档调整；核心思路不变。

---

## 10. 小结

本章完成了红外遥控的端到端链路：硬件接入（接收头与发射驱动）、NEC 协议的稳健解码（`time_pulse_us`）与 RMT 发码（38kHz 载波），并给出长按重复处理与动作映射。实战建议优先锁定 NEC 协议，先“学习打印”再绑定动作；发射端务必用三极管驱动 IR LED，并确保载波频率与时序可靠。若需要支持更多协议或“学习器”功能，可在 RMT 基础上扩展“原始脉冲捕获/重放”。
