# 第二十七章 低功耗模式与深度睡眠 (Deep Sleep)

## 1. 导入

在前几章中，我们让 ESP32 连接 WiFi 并使用 MQTT 发送数据。虽然功能很强大，但有一个**致命弱点**：功耗。

- **正常工作 (WiFi 开启)**：电流约 **80mA ~ 240mA**。用一块 2000mAh 的电池，不到一天就没电了。
- **深度睡眠 (Deep Sleep)**：电流约 **10µA ~ 150µA**。同样的电池可以用 **几个月甚至一年**。

**工作原理**：  
进入 Deep Sleep 后，ESP32 会关闭 CPU、WiFi、蓝牙和大部分外设，只保留 **RTC (实时时钟)** 控制器运行。当达到设定时间或被外部引脚触发时，它会**唤醒**。  
**注意**：唤醒相当于**复位 (Reset)**，程序会从头开始运行，RAM 中的变量会丢失（除非存在 RTC 内存中）。

---

## 2. 核心函数

```python
import machine

# 进入深度睡眠
# 参数：毫秒 (ms)。如果不填，则无限睡眠直到被引脚唤醒。
machine.deepsleep(5000) 

# 检查复位原因 (判断是刚上电还是睡醒了)
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print("我是从睡梦中醒来的")
else:
    print("我是冷启动(上电/按复位键)")
```

> **⚠️ 避免“变砖”死循环**：  
> 如果你的代码一启动就立刻进入睡眠，你将无法通过 USB 上传新代码。  
> **解决办法**：在 `main.py` 开头加一个 `time.sleep(3)`，给你 3 秒钟的时间在 Thonny 中点击“Stop”中断程序。

---

## 3. 实战一：定时唤醒 (周期性上报)

这是最常见的场景：每隔 10 秒醒来一次，打印一句话（模拟采集传感器），然后继续睡。

```python
import machine
import time

# --- 1. 防止死循环的安全机制 ---
# 给你 3 秒钟时间按 Ctrl+C 中断，否则烧录进去后很难再次连接
print("程序启动，3秒内按 Ctrl+C 可中断...")
time.sleep(3)

# --- 2. 判断唤醒原因 ---
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print(">>> 唤醒类型: 定时唤醒")
else:
    print(">>> 唤醒类型: 首次上电")

# --- 3. 模拟工作任务 ---
print("正在连接传感器...")
time.sleep(1) # 模拟耗时操作
print("正在发送 MQTT 数据...")
time.sleep(1) # 模拟 WiFi 发送耗时
print("任务完成，准备睡觉。")

# --- 4. 进入深度睡眠 ---
# 睡眠 5000 毫秒 (5秒)
print("进入 Deep Sleep 5秒...")
machine.deepsleep(5000)
```

**实验现象**：  
你会看到串口不断重启打印信息，但中间会断开连接。因为睡眠时 USB 串口也会断电。

---

## 4. 实战二：外部引脚唤醒 (按键触发)

场景：智能门铃。平时完全休眠，只有当客人按下按钮（GPIO 电平变化）时才醒来工作。

**注意**：只有 **RTC GPIO** 才能唤醒 ESP32。  
常见的 RTC GPIO：`GPIO 0, 2, 4, 12, 13, 14, 15, 25, 26, 27, 32-39`。

```python
import machine
import esp32
import time
from machine import Pin

# 定义唤醒引脚 (这里用 GPIO 13，你需要接一个按钮连接到 3.3V)
# 注意：配置为 PULL_DOWN (下拉)，这样平时是低电平，按下是高电平
wake_pin = Pin(13, mode=Pin.IN, pull=Pin.PULL_DOWN)

# 配置唤醒源
# esp32.WAKEUP_ANY_HIGH: 任意高电平唤醒
# esp32.WAKEUP_ALL_LOW:  低电平唤醒
esp32.wake_on_ext0(pin=wake_pin, level=esp32.WAKEUP_ANY_HIGH)

print("程序启动，3秒后进入休眠...")
time.sleep(3)

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print(">>> 被按钮叫醒了！")
else:
    print(">>> 系统上电")

print("处理业务中...")
for i in range(3):
    print(f"工作 {i+1}/3")
    time.sleep(0.5)

print("工作结束，等待下一次按键...")
machine.deepsleep() # 无限睡眠，直到被唤醒
```

---

## 5. 进阶：使用 RTC 内存保存数据

因为 Deep Sleep 唤醒等于复位，`count = 0` 这种变量会重置。  
如果我们想记录“这是第几次唤醒”，需要将数据存在 **RTC Memory** 中（睡眠时这部分内存不断电）。

MicroPython 的 `machine.RTC().memory()` 可以存取二进制数据。

```python
import machine
import time
import struct

# --- 安全延时 ---
time.sleep(2)

# 获取 RTC 对象
rtc = machine.RTC()

# --- 读取 RTC 内存 ---
# 内存默认为空或随机，需要处理
data = rtc.memory()

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    # 如果是唤醒的，尝试解析数据
    try:
        # 使用 struct 解包：'i' 代表 integer (整数)
        count = struct.unpack('i', data)[0]
    except:
        count = 0
else:
    # 如果是冷启动，重置计数
    count = 0

# --- 业务逻辑 ---
count += 1
print(f"这是第 {count} 次唤醒")

# --- 写入 RTC 内存 ---
# 将整数打包成二进制存入 RTC
rtc.memory(struct.pack('i', count))

# --- 继续睡觉 ---
print("睡觉 3秒...")
machine.deepsleep(3000)
```

---

## 6. 低功耗 WiFi 连接策略 (实战技巧)

在电池供电项目中，连接 WiFi 是最耗电的环节。为了省电，我们应当：

1. **静态 IP**：避免 DHCP 耗时（DHCP 需要几秒，静态 IP 毫秒级）。
2. **做完即睡**：一连上 MQTT 发完数据马上睡。

```python
import network
import machine
import time

# ... (安全延时代码) ...

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# 【优化】设置静态 IP，大幅加快连接速度
# 格式: (IP, 子网掩码, 网关, DNS)
# 请根据你路由器的网段修改
wlan.ifconfig(('192.168.1.200', '255.255.255.0', '192.168.1.1', '8.8.8.8'))

wlan.connect('SSID', 'PASSWORD')

# 等待连接 (增加超时跳出，防止连不上一直耗电)
attempt = 0
while not wlan.isconnected() and attempt < 20:
    attempt += 1
    time.sleep(0.1)

if wlan.isconnected():
    print("联网成功，发送数据...")
    # do_mqtt_publish()
else:
    print("联网失败，跳过本次任务")

print("立即休眠")
machine.deepsleep(60000) # 睡 1 分钟
```

## 7. 小结

本章让你的 ESP32 具备了“续航能力”。

- **Deep Sleep** 是电池供电项目的必修课。
- **唤醒机制**：定时 (Timer) 和 触控/按键 (Ext0/Ext1)。
- **数据保存**：使用 RTC Memory 跨睡眠周期保存关键变量。

---


