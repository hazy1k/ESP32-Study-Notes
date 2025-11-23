# 第十五章 RTC 实时时钟

## 1. 导入

ESP32 有片上 RTC 计时器，但其长期走时精度一般，需要定期校时。工程上常用三种方式获得“靠谱的时间”：

- 内部 RTC：用 `machine.RTC` 保存时间，结合深度睡眠可低功耗运行，需外部校时。
- NTP 网络校时：上电连网后调用 NTP 同步（UTC），再根据时区显示本地时间。
- 外部硬件 RTC：如 DS3231（高精度，带温补与电池），断电仍能保持时间；上电先从外部 RTC 取时，再选用 NTP 精校并回写。

本章给出以上方案的完整代码：基础 `RTC` 用法、NTP 校时、DS3231 驱动与互相同步，时区处理，周期重校，及与深度睡眠配合。

## 2. 硬件设计

- 外部 RTC 推荐：DS3231（I2C，可靠、温补、带电池）、次选 DS1307（精度一般）。
- 典型接线（DS3231 模块）：

```c
ESP32 3V3  -> DS3231 VCC     // 多数小板 3.3V/5V 兼容
ESP32 GND  -> DS3231 GND
ESP32 GPIO21 -> DS3231 SDA   // I2C 数字引脚可改
ESP32 GPIO22 -> DS3231 SCL   // 默认 I2C
（可选）DS3231 INT/SQW -> ESP32 可中断的 RTC IO（用于闹钟唤醒）
```

- I2C 上拉：模块常自带 4.7kΩ 上拉，无需另加；若总线上设备多、线长，注意总上拉等效值与速率。
- 纽扣电池：DS3231 模块插入 CR2032 以断电保持时间。

## 3. 软件设计

- 目标：
  - 初始化系统时间（优先外部 RTC → 其次 NTP）。
  - 时区与本地时间显示。
  - 周期性对时（避免长期漂移）。
  - 可选将 NTP 时间回写 DS3231，统一时间源。
- 关键模块：
  - `machine.RTC`、`time`/`utime`：系统时间基础。
  - `network`、`ntptime`：连接 Wi‑Fi、NTP 校时。
  - `machine.I2C`：外部 DS3231 通信。
  - `uasyncio` 或 `Timer`：周期任务。

---

## 4. 基础：内部 RTC 读写与显示

说明：部分固件使用不同“纪元”（1970/2000），但 `time.time()/localtime()/mktime()` 自洽。统一用 `time.localtime()` 与 `time.time()` 即可；NTP 设置的是 UTC，显示本地时间时再加时区偏移。

```python
# 文件：rtc_basic.py
import machine, time

rtc = machine.RTC()

def set_rtc(y, mo, d, h, mi, s):
    # 计算星期（0..6，通常 0=Monday），用 mktime/localtime 自洽计算
    secs = time.mktime((y, mo, d, h, mi, s, 0, 0))
    wday = time.localtime(secs)[6]
    rtc.datetime((y, mo, d, wday, h, mi, s, 0))

def now_local(tz=0):
    # tz: 时区小时偏移（如中国大陆 +8）
    return time.localtime(time.time() + tz*3600)

def fmt(ts):
    y,mo,d,hh,mm,ss = ts[0], ts[1], ts[2], ts[3], ts[4], ts[5]
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(y,mo,d,hh,mm,ss)

# 示例：手动设定时间并打印（仅演示）
# set_rtc(2025, 1, 1, 12, 0, 0)
print("Local:", fmt(now_local(tz=8)))
```

---

## 5. NTP 网络校时（UTC）+ 时区显示

```python
# 文件：rtc_ntp.py
import network, time, ntptime, machine

def wifi_connect(ssid, pwd, timeout=10):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(ssid, pwd)
        t0 = time.ticks_ms()
        while (not sta.isconnected()) and time.ticks_diff(time.ticks_ms(), t0) < timeout*1000:
            time.sleep_ms(200)
    return sta.isconnected(), sta.ifconfig() if sta.isconnected() else None

def ntp_sync(host="pool.ntp.org", retries=3, delay=1.0):
    ntptime.host = host
    for _ in range(retries):
        try:
            ntptime.settime()  # 设置系统 RTC 为 UTC
            return True
        except Exception as e:
            time.sleep(delay)
    return False

def now_local(tz=0):
    return time.localtime(time.time() + tz*3600)

def fmt(ts):
    y,mo,d,hh,mm,ss = ts[0], ts[1], ts[2], ts[3], ts[4], ts[5]
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(y,mo,d,hh,mm,ss)

if __name__ == "__main__":
    ok, info = wifi_connect("your-ssid", "your-pass")
    print("WiFi:", ok, info)
    if ok and ntp_sync():
        print("UTC:", fmt(time.gmtime()))
        print("CST(+8):", fmt(now_local(8)))
    else:
        print("NTP 同步失败，保持当前 RTC")
```

要点：

- `ntptime.settime()` 将系统时间设为 UTC；显示本地时区通过 `tz` 偏移处理。
- 可用 `uasyncio` 每隔数小时重校一次（见第 8 节）。

---

## 6. 外部硬件 RTC：DS3231 驱动（I2C）

- 读写寄存器 0x00..0x06（秒~年，BCD 编码），采用 24h 模式。
- 提供温度读取（0x11、0x12，可选）。

```python
# 文件：ds3231.py
from machine import I2C, Pin
import time

DS3231_ADDR = 0x68

def _bcd2i(x): return (x >> 4) * 10 + (x & 0x0F)
def _i2bcd(x): return ((x // 10) << 4) | (x % 10)

class DS3231:
    def __init__(self, i2c: I2C, addr=DS3231_ADDR):
        self.i2c = i2c
        self.addr = addr

    def present(self):
        return self.addr in self.i2c.scan()

    def datetime(self):
        # 返回 (year, month, day, hour, minute, second)
        data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
        ss = _bcd2i(data[0] & 0x7F)          # CH 位清除
        mm = _bcd2i(data[1])
        h  = data[2]
        if h & 0x40:                          # 12h 模式不支持，要求 24h
            raise ValueError("DS3231 in 12h mode")
        hh = _bcd2i(h & 0x3F)
        # data[3] = day of week (1..7)，此处忽略
        dd = _bcd2i(data[4])
        mo = _bcd2i(data[5] & 0x1F)
        yy = _bcd2i(data[6]) + 2000
        return (yy, mo, dd, hh, mm, ss)

    def set_datetime(self, y, mo, d, hh, mm, ss):
        # 设置 24h 模式、清除 CH
        buf = bytearray(7)
        buf[0] = _i2bcd(ss & 0x7F)           # CH=0
        buf[1] = _i2bcd(mm)
        buf[2] = _i2bcd(hh)                  # 24h
        # 星期占位（1=Mon..7），我们写 1
        buf[3] = 1
        buf[4] = _i2bcd(d)
        buf[5] = _i2bcd(mo)                  # Century 位忽略
        buf[6] = _i2bcd((y - 2000) % 100)
        self.i2c.writeto_mem(self.addr, 0x00, buf)

    def temperature(self):
        msb = self.i2c.readfrom_mem(self.addr, 0x11, 1)[0]
        lsb = self.i2c.readfrom_mem(self.addr, 0x12, 1)[0]
        return msb + (lsb >> 6) * 0.25

def init_i2c(scl=22, sda=21, freq=100_000):
    return I2C(0, scl=Pin(scl), sda=Pin(sda), freq=freq)
```

示例：读外部 RTC，设置系统时间并打印本地时间

```python
# 文件：main_ds3231.py
import machine, time
from ds3231 import DS3231, init_i2c

def set_system_rtc_from(y, mo, d, hh, mm, ss):
    rtc = machine.RTC()
    secs = time.mktime((y, mo, d, hh, mm, ss, 0, 0))
    wday = time.localtime(secs)[6]
    rtc.datetime((y, mo, d, wday, hh, mm, ss, 0))

def now_local(tz=8):
    return time.localtime(time.time() + tz*3600)

i2c = init_i2c()
chip = DS3231(i2c)
if chip.present():
    y,mo,d,hh,mm,ss = chip.datetime()
    set_system_rtc_from(y,mo,d,hh,mm,ss)
    print("DS3231 -> RTC:", "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(y,mo,d,hh,mm,ss))
    print("Local(+8):", now_local(8))
else:
    print("未发现 DS3231（0x68），请检查 I2C 接线")
```

---

## 7. 统一时钟管理：优先外部 RTC → 其次 NTP，并回写

- 上电流程：
  1. 若检测到 DS3231，先取时并设置系统 RTC。
  2. 若有网络，NTP 精校系统时间，再回写 DS3231。
  3. 打印当前本地时间（含时区）；后续周期性重校。

```python
# 文件：rtc_manager.py
import machine, time, network, ntptime
from ds3231 import DS3231, init_i2c

def wifi_connect(ssid, pwd, timeout=10):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(ssid, pwd)
        t0 = time.ticks_ms()
        while (not sta.isconnected()) and time.ticks_diff(time.ticks_ms(), t0) < timeout*1000:
            time.sleep_ms(200)
    return sta.isconnected()

def set_sys_rtc(y, mo, d, hh, mm, ss):
    rtc = machine.RTC()
    secs = time.mktime((y, mo, d, hh, mm, ss, 0, 0))
    wday = time.localtime(secs)[6]
    rtc.datetime((y, mo, d, wday, hh, mm, ss, 0))

def now_local(tz=0):
    return time.localtime(time.time() + tz*3600)

def fmt(ts):
    y,mo,d,hh,mm,ss = ts[0], ts[1], ts[2], ts[3], ts[4], ts[5]
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(y,mo,d,hh,mm,ss)

def boot_sync(tz=8, ssid=None, pwd=None, use_ds3231=True, ntp_host="pool.ntp.org"):
    # 1) 外部 RTC
    chip = None
    if use_ds3231:
        try:
            chip = DS3231(init_i2c())
            if chip.present():
                y,mo,d,hh,mm,ss = chip.datetime()
                set_sys_rtc(y,mo,d,hh,mm,ss)
                print("[RTC] DS3231 提供时间:", fmt((y,mo,d,hh,mm,ss)))
        except Exception as e:
            print("[RTC] DS3231 读取失败：", e)

    # 2) NTP
    if ssid and pwd:
        if wifi_connect(ssid, pwd):
            try:
                ntptime.host = ntp_host
                ntptime.settime()
                # 回写外部 RTC（若存在）
                if chip and chip.present():
                    # 以 UTC 写入，再依据显示时区处理
                    y,mo,d,hh,mm,ss,_,_ = time.gmtime()
                    chip.set_datetime(y,mo,d,hh,mm,ss)
                    print("[RTC] 已回写 DS3231(UTC)")
                print("[RTC] NTP 已同步：UTC", fmt(time.gmtime()))
            except Exception as e:
                print("[RTC] NTP 同步失败：", e)

    print("[RTC] 本地时间(+{}):".format(tz), fmt(now_local(tz)))
    return True
```

使用：

```python
# 文件：main.py
from rtc_manager import boot_sync
import time

boot_sync(tz=8, ssid="your-ssid", pwd="your-pass", use_ds3231=True)
while True:
    print("tick", time.time())
    time.sleep(1)
```

---

## 8. 周期性重校与非阻塞运行

- 推荐在联网设备中每 6~24 小时执行一次 NTP 重校。
- uasyncio 版本（若无 asyncio，可用 `Timer` 周期触发一个轻量任务）：

```python
# 文件：rtc_resync.py
import uasyncio as asyncio, ntptime, time

async def periodic_ntp(hours=6, host="pool.ntp.org"):
    while True:
        try:
            ntptime.host = host
            ntptime.settime()
            print("[RTC] NTP 重校完成 UTC:", time.gmtime())
        except Exception as e:
            print("[RTC] NTP 重校失败：", e)
        await asyncio.sleep(hours * 3600)

async def main():
    asyncio.create_task(periodic_ntp(hours=12))
    while True:
        # 你的业务逻辑
        await asyncio.sleep(1)

asyncio.run(main())
```

---

## 9. 深度睡眠与唤醒

- 内部 RTC 在深度睡眠期间继续计时；唤醒后程序从头执行，请在启动阶段做一次 `boot_sync()`（优先外部 RTC 取时，无网也能正确显示）。
- 定时唤醒（内部定时器）：

```python
# 文件：deepsleep_demo.py
import machine, time
from rtc_manager import boot_sync

boot_sync(tz=8, ssid=None, pwd=None)  # 无网也能用外部 RTC 取时
print("Do work @", time.localtime())
machine.deepsleep(60_000)  # 睡眠 60 秒后唤醒
```

- DS3231 闹钟唤醒（可选）：将 DS3231 的 INT/SQW 接至 ESP32 RTC IO，配置 EXT0/EXT1 唤醒。DS3231 闹钟寄存器配置较繁，本章不展开；通常用内部定时唤醒更简单。

---

## 10. 时区与夏令时（概览）

- MicroPython 不带完整时区数据库；最简方式是固定时区偏移 `tz`（小时），显示本地时间时用 `time.time() + tz*3600`。
- 夏令时可用“规则函数”在切换日期自动调整 `tz`，或在配置中切换一个布尔值 `DST`。

---

## 11. 常见问题与排查

- 上电时间错乱：
  - 未做校时；请用外部 DS3231 或 NTP；或将外部 RTC 的电池装好后手动设置一次。
- NTP 成功但本地时间不对：
  - NTP 设置的是 UTC；请显示时加上正确的时区偏移。
- DS3231 不响应：
  - I2C 线接反/SDA、SCL 选错；地址应为 0x68；检查上拉与供电。
  - 芯片处在 12h 模式；本驱动要求 24h（默认 OK，若不是，请清 12h 位）。
- 深度睡眠后时间跳变：
  - 启动代码未恢复外部 RTC/未连网校时；确保在 `boot.py`/`main.py` 开头调用 `boot_sync()`。
- 长期漂移：
  - 仅用内部 RTC 会慢慢漂移；增加 NTP 周期重校，或以 DS3231 为主时钟源并偶尔 NTP 精校。

---

## 12. 小结

本章构建了完整的“实时时钟体系”：基础 `machine.RTC` 用法、NTP 校时与时区显示、外部 DS3231 驱动与回写、周期性重校及与深度睡眠的协同。工程建议是：上电优先从 DS3231 读取时间保证“即刻正确”，若网络可用再 NTP 精校并回写 DS3231；运行中低频率重校，显示时用固定时区或规则处理夏令时。通过这一组合，可在绝大多数场景获得稳定、准确的系统时间。

---
