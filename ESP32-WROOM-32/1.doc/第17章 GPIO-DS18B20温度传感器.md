# 第十七章 DS18B20 温度传感器

## 1. 导入

DS18B20 是单总线（1-Wire）数字温度传感器，精度典型 ±0.5°C（-10~85°C），支持多只并联在同一根数据线上。它的优势是接线简单（仅数据线+上拉），读取稳定，且每颗器件都有唯一 64 位 ROM 地址，易于多点测温。

本章覆盖硬件接线与上拉、电源与寄生供电的差异、MicroPython 驱动与单/多传感器读取、分辨率设置（9~12 bit）、异步采集，以及常见问题排查。

## 2. 硬件设计

- 供电方式：
  - 正常供电（推荐）：VDD 接 3.3V，DQ 数据线使用 4.7kΩ 上拉到 3.3V，GND 共地。最稳定。
  - 寄生供电（不建议入门使用）：VDD 接 GND，仅靠数据线汲取能量。对“强上拉”要求高，长线/多器件场景容易不稳。
- 典型接线（正常供电，推荐）：

```c
ESP32 3V3  -> DS18B20 VDD
ESP32 GND  -> DS18B20 GND
ESP32 GPIO4 -> DS18B20 DQ（数据）
           |
           +-- 4.7kΩ 上拉 --→ 3V3
（多只并联：所有 DS18B20 的 DQ 并在一起，共用一个 4.7kΩ 上拉）
```

- 引脚与线长：
  - 使用任意可用 GPIO 作为 1-Wire 数据脚（如 4/5/16/17/18/19/21/22/23/25/26/27/32/33）。
  - 线越短越好；长线（>2~3m）时可适当降低采样频率、优化布线/屏蔽，必要时分段/加缓冲。
- 负载与自热：
  - 频繁转换会带来轻微自热，建议 ≥1s 间隔读取。

## 3. 软件设计

- 关键模块：
  - `onewire`：1-Wire 低层时序。
  - `ds18x20`：DS18B20 高层封装（扫描、启动转换、读温度）。
  - `time`、`uasyncio`：时序/异步。
- 分辨率与转换时间（典型，越高越慢）：
  - 9 bit：93.75 ms
  - 10 bit：187.5 ms
  - 11 bit：375 ms
  - 12 bit：750 ms（默认）

---

## 4. 快速上手：单只传感器读取

```python
# 文件：main.py
from machine import Pin
import onewire, ds18x20, time

DATA_PIN = 4  # 按你的接线修改

ow = onewire.OneWire(Pin(DATA_PIN))
ds = ds18x20.DS18X20(ow)

roms = ds.scan()
if not roms:
    raise RuntimeError("未发现 DS18B20，请检查接线与上拉电阻")
print("发现器件：", [rom.hex() for rom in roms])

rom = roms[0]  # 仅用第一只，多个请见下一节

while True:
    ds.convert_temp()       # 触发所有器件温度转换
    time.sleep_ms(750)      # 12-bit 转换时间；若降低分辨率可缩短
    t = ds.read_temp(rom)   # 摄氏度，float
    print("T = {:.2f} °C".format(t if t is not None else float('nan')))
    time.sleep(1)
```

要点：

- `ds.convert_temp()` 会同时触发“总线上所有 DS18B20”转换，一次等待后可依次读取各只的测温结果。
- 初次上电若马上读到 85.0°C，多半是“未等待转换完成”的默认值，确保等待时间足够。

---

## 5. 多传感器并联读取

```python
# 文件：read_multi.py
from machine import Pin
import onewire, ds18x20, time

ow = onewire.OneWire(Pin(4))
ds = ds18x20.DS18X20(ow)

roms = ds.scan()
print("总线设备：", [rom.hex() for rom in roms])
if not roms:
    raise RuntimeError("未发现传感器")

def read_all():
    ds.convert_temp()
    time.sleep_ms(750)
    vals = {}
    for r in roms:
        vals[r.hex()] = ds.read_temp(r)
    return vals

while True:
    temps = read_all()
    print({k: round(v, 2) if v is not None else None for k, v in temps.items()})
    time.sleep(1)
```

技巧：

- 建议把 `rom.hex()` 存为配置文件中的“友好 ID”，便于固定每路传感器的逻辑名称（例如 “inlet”, “outlet”, “room1” 等）。

---

## 6. 分辨率设置（9/10/11/12-bit）与报警寄存器

标准驱动未直接提供“改分辨率”，可用底层 OneWire 指令写入 Scratchpad，并复制到 EEPROM。

```python
# 文件：ds18b20_cfg.py
from machine import Pin
import onewire, ds18x20, time

# DS18B20 命令
CMD_SKIP_ROM      = 0xCC
CMD_MATCH_ROM     = 0x55
CMD_CONVERT_T     = 0x44
CMD_READ_SCRATCH  = 0xBE
CMD_WRITE_SCRATCH = 0x4E
CMD_COPY_SCRATCH  = 0x48
CMD_READ_POWSUP   = 0xB4

RES_CFG = {
    9:  0x1F,
    10: 0x3F,
    11: 0x5F,
    12: 0x7F,
}

class DS18B20Cfg:
    def __init__(self, pin):
        self.ow = onewire.OneWire(Pin(pin))
        self.ds = ds18x20.DS18X20(self.ow)

    def scan(self):
        return self.ds.scan()

    def read_power_mode(self, rom):
        """
        返回 'normal' 或 'parasite'
        """
        self.ow.reset()
        self.ow.select_rom(rom)
        self.ow.writebyte(CMD_READ_POWSUP)
        bit = self.ow.readbit()   # 1=外部供电，0=寄生供电
        return 'normal' if bit == 1 else 'parasite'

    def read_scratchpad(self, rom):
        self.ow.reset()
        self.ow.select_rom(rom)
        self.ow.writebyte(CMD_READ_SCRATCH)
        data = bytearray(9)
        for i in range(9):
            data[i] = self.ow.readbyte()
        return data  # [tempL,tempH,TH,TL,CFG, ... , CRC]

    def set_resolution(self, rom, res_bits=12, th=75, tl=70):
        """
        res_bits: 9/10/11/12
        th/tl: 报警阈值寄存器（单位 °C，整数）
        """
        conf = RES_CFG.get(int(res_bits))
        if conf is None:
            raise ValueError("分辨率必须为 9/10/11/12")
        # 写 Scratchpad：TH, TL, CFG
        self.ow.reset()
        self.ow.select_rom(rom)
        self.ow.writebyte(CMD_WRITE_SCRATCH)
        self.ow.writebyte(th & 0xFF)
        self.ow.writebyte(tl & 0xFF)
        self.ow.writebyte(conf & 0xFF)
        # 复制到 EEPROM（耗时，需等待）
        self.ow.reset()
        self.ow.select_rom(rom)
        self.ow.writebyte(CMD_COPY_SCRATCH)
        time.sleep_ms(15)  # t_WR 10ms 以上
        # 读回确认
        sc = self.read_scratchpad(rom)
        ok = (sc[4] == conf)
        return ok

if __name__ == "__main__":
    cfg = DS18B20Cfg(pin=4)
    roms = cfg.scan()
    print([r.hex() for r in roms])
    if roms:
        rom = roms[0]
        print("供电方式:", cfg.read_power_mode(rom))
        print("设置分辨率->10bit:", cfg.set_resolution(rom, 10))
```

说明：

- 分辨率越低，转换时间越短，适合快速/多点采样场景（如 10bit ≈ 187.5ms）。
- 若使用寄生供电，某些模块在“复制 Scratchpad”时需要强上拉，ESP32 直接驱动可能失败；尽量用正常供电。

---

## 7. 异步采集（uasyncio）

一次 `convert_temp()` 触发总线上所有传感器转换；等待期间可并发执行其他任务。

```python
# 文件：read_async.py
from machine import Pin
import onewire, ds18x20
import uasyncio as asyncio

ow = onewire.OneWire(Pin(4))
ds = ds18x20.DS18X20(ow)
roms = ds.scan()
print([r.hex() for r in roms])

async def read_all(period_ms=1000, tconv_ms=750):
    while True:
        ds.convert_temp()
        await asyncio.sleep_ms(tconv_ms)  # 根据分辨率调整
        vals = {}
        for r in roms:
            vals[r.hex()] = ds.read_temp(r)
        print({k: round(v,2) if v is not None else None for k,v in vals.items()})
        # 距离下一周期
        remain = max(0, period_ms - tconv_ms)
        await asyncio.sleep_ms(remain)

asyncio.run(read_all(period_ms=1500, tconv_ms=375))  # 例如 11bit
```

---

## 8. 实用封装：多路测温管理器

```python
# 文件：ds18b20_mgr.py
from machine import Pin
import onewire, ds18x20, time

class DS18B20Manager:
    def __init__(self, pin, rom_alias=None, tconv_ms=750):
        """
        rom_alias: {rom_hex: name} 的映射（可选）
        tconv_ms: 转换等待（按分辨率调整）
        """
        self.ow = onewire.OneWire(Pin(pin))
        self.ds = ds18x20.DS18X20(self.ow)
        self.roms = self.ds.scan()
        if not self.roms:
            raise RuntimeError("未发现 DS18B20")
        self.alias = rom_alias or {}
        self.tconv = int(tconv_ms)

    def names(self):
        out = []
        for r in self.roms:
            hx = r.hex()
            out.append(self.alias.get(hx, hx))
        return out

    def read_all(self, retry=1):
        """
        阻塞式批量读取，返回 {name_or_hex: tempC}
        """
        res = {}
        for _ in range(retry+1):
            self.ds.convert_temp()
            time.sleep_ms(self.tconv)
            ok = True
            for r in self.roms:
                name = self.alias.get(r.hex(), r.hex())
                try:
                    t = self.ds.read_temp(r)
                    if t is None:
                        ok = False
                    res[name] = t
                except OSError:
                    ok = False
                    res[name] = None
            if ok:
                break
        return res
```

使用：

```python
# 文件：main.py
from ds18b20_mgr import DS18B20Manager
import time

aliases = {
    "28ffe1a2b0123456": "inlet",
    "28ff98c3d0654321": "outlet",
}
mgr = DS18B20Manager(pin=4, rom_alias=aliases, tconv_ms=375)  # 11bit

while True:
    temps = mgr.read_all()
    print({k: round(v,2) if v else None for k,v in temps.items()})
    time.sleep(1)
```

---

## 9. 常见问题与排查

- 读到 85.0°C：
  - 典型“未完成转换”的默认值；确保 `convert_temp()` 后等待足够的 t_conv（依据分辨率）。
- 读到 -127.0°C 或 None：
  - 总线错误/未拉起/连线问题；检查 4.7kΩ 上拉、电源与 GND、DQ 是否接对。
- 多只并联不稳定：
  - 线过长或星形布线导致反射/时序问题；改为总线/树状拓扑，降低采样频率，确保上拉就近，必要时缩短线缆。
- 寄生供电异常：
  - 复制 Scratchpad 或转换阶段需要强上拉；ESP32 直接驱动可能失败。尽量使用正常 3.3V 供电。
- 数值抖动：
  - 正常的 ±0.2°C 抖动可通过移动平均/IIR 滤波平滑；注意避免高频读取引发自热。
- 精度与校准：
  - 多只个体存在微小偏差，可与标准温计对比后做软件偏移校正（例如每路加/减 0.2°C）。

---

## 10. 小结

本章完成了 DS18B20 的稳定接线与 MicroPython 读取：单/多传感器的扫描、批量转换与读取；给出了分辨率配置与供电方式检测，以及基于 uasyncio 的非阻塞采集与多路管理封装。实践中优先使用“正常供电+4.7kΩ 上拉”，并根据分辨率合理设置等待时间与采样周期，即可获得可靠的温度数据。

---
