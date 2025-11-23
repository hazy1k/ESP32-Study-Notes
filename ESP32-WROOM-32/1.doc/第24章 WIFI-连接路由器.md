# 第二十四章 WIFI-连接路由器 (Station模式)

## 1. 导入

ESP32 之所以被称为“物联网神卡”，核心原因就在于它集成了强大的 Wi-Fi 和蓝牙功能。  
在 Wi-Fi 开发中，主要有两种模式：

1. **AP 模式 (Access Point)**：ESP32 自己产生热点，手机连接它（像配置路由器一样）。
2. **STA 模式 (Station)**：ESP32 像手机一样连接家里的路由器（本章重点）。

连接上路由器后，ESP32 就拥有了访问互联网的能力，可以进行 NTP 对时、MQTT 通信、HTTP 请求等操作。

---

## 2. 核心库与函数

MicroPython 使用内置的 `network` 模块来管理网络。

- **初始化接口**：
  
  ```python
  import network
  wlan = network.WLAN(network.STA_IF) # 创建 STA 接口对象
  wlan.active(True)                   # 激活 Wi-Fi 接口
  ```

- **扫描网络**（可选）：
  
  ```python
  wlan.scan() # 返回列表：(ssid, bssid, channel, RSSI, authmode, hidden)
  ```

- **连接**：
  
  ```python
  wlan.connect('你的WiFi名称', '你的WiFi密码')
  ```

- **检查状态**：
  
  ```python
  wlan.isconnected() # 返回 True/False
  wlan.status()      # 返回连接状态码
  wlan.ifconfig()    # 返回元组：(IP, 子网掩码, 网关, DNS)
  ```

---

## 3. 基础连接代码（入门版）

这是最简单的连接方式，适合快速测试，但缺乏超时处理，如果密码错误会一直死循环。

```python
import network
import time

# 这里填入你的 WiFi 信息
SSID = "Your_WiFi_Name"
PASSWORD = "Your_WiFi_Password"

def connect_simple():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print('正在连接到网络...')
        wlan.connect(SSID, PASSWORD)

        # 等待连接，这里是死循环，实际使用建议加超时
        while not wlan.isconnected():
            time.sleep(1)
            print(".", end="")

    print('\n网络配置:', wlan.ifconfig())

# 运行
connect_simple()
```

---

## 4. 稳健连接封装（工业级推荐）

在实际项目中，网络环境复杂，我们需要处理**连接超时**、**连接失败**等情况，并给出明确的反馈。以下是一个封装好的通用函数。

```python
import network
import time

def connect_wifi(ssid, password, timeout_sec=10):
    """
    连接 WiFi 的稳健封装
    :param ssid: WiFi 名称
    :param password: WiFi 密码
    :param timeout_sec: 超时时间(秒)
    :return: True 连接成功, False 连接失败
    """
    # 1. 初始化接口
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # 2. 如果已经连接，直接返回
    if wlan.isconnected():
        print("WiFi 已连接")
        print("IP 信息:", wlan.ifconfig())
        return True

    print(f"开始连接 WiFi: {ssid} ...")
    wlan.connect(ssid, password)

    # 3. 循环检测连接状态 (带超时机制)
    start_time = time.time()
    while not wlan.isconnected():
        # 检查是否超时
        if time.time() - start_time > timeout_sec:
            print("\n错误: WiFi 连接超时!")
            return False

        time.sleep(0.5)
        print(">", end="")

    # 4. 连接成功
    print("\n连接成功!")
    config = wlan.ifconfig()
    print(f"IP地址: {config[0]}")
    print(f"子网掩码: {config[1]}")
    print(f"网关: {config[2]}")
    print(f"DNS: {config[3]}")
    return True

# --- 使用示例 ---
# 请修改为你的真实账号密码
MY_SSID = "Xiaomi_2.4G" 
MY_PASS = "12345678"

if connect_wifi(MY_SSID, MY_PASS):
    print("主程序继续运行...")
    # 这里可以放你的业务代码
else:
    print("网络连接失败，请检查密码或路由器。")
```

---

## 5. 实战：连接网络后自动对时 (NTP)

ESP32 断电后时间会重置。既然连上了网，第一件事通常是校准时间。MicroPython 内置了 `ntptime` 模块。

```python
import time
import ntptime
# 确保你已经运行了上面的 connect_wifi 并成功连接

def sync_time():
    print("正在同步网络时间...")
    try:
        # 默认连接 pool.ntp.org
        ntptime.host = 'ntp1.aliyun.com' # 推荐改用阿里云 NTP，国内速度快
        ntptime.settime() # 这会将时间设置为 UTC (格林威治时间)
        print("时间同步成功!")

        # 调整时区 (UTC+8 北京时间)
        # MicroPython 的 RTC 是硬件时钟，我们要手动加 8 小时秒数
        # 8小时 = 8 * 3600 = 28800 秒
        import machine
        rtc = machine.RTC()
        # 获取当前 UTC 时间
        utc_time = time.time()
        # 加上偏移量
        local_time_sec = utc_time + 28800 
        # 重新转换为元组格式 (year, month, day, hour, minute, second, weekday, yearday)
        tm = time.localtime(local_time_sec)

        # 为了方便显示，可以简单格式化一下
        print("当前北京时间: {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            tm[0], tm[1], tm[2], tm[3], tm[4], tm[5]))

    except Exception as e:
        print("时间同步失败:", e)

# 调用
# connect_wifi(MY_SSID, MY_PASS) # 确保已联网
sync_time()
```

---

## 6. 常见问题与排查

1. **不支持 5G WiFi**：
   - **致命问题**：ESP32 **仅支持 2.4GHz频段** 的 WiFi。如果你的路由器是 5G 频段，或者双频合一但引导到了 5G，ESP32 是搜不到也连不上的。请确保连接的是 2.4G 信号。
2. **IP 地址为 0.0.0.0**：
   - 表示虽然 `wlan.active(True)` 了，但还没有获取到 DHCP 分配的 IP。需要等待 `wlan.isconnected()` 变为 True。
3. **供电不足**：
   - WiFi 射频启动瞬间电流很大（瞬时可达 300mA+）。如果使用劣质 USB 线或电脑 USB 口供电不足，ESP32 可能会复位（Brownout）。
4. **天线信号**：
   - **ESP32-WROOM**：板载 PCB 天线，注意天线部分不要被金属遮挡。
   - **ESP32-CAM**：通常需要外接 IPEX 天线。如果不接天线，信号极差，距离路由器超过 1 米可能就断连。

## 7. 小结

本章我们成功让 ESP32 接入了互联网，并获取了准确的时间。

- **核心对象**：`network.WLAN(network.STA_IF)`
- **关键动作**：`.active(True)` -> `.connect()` -> `.isconnected()`
- **下一步**：既然连上了网，下一章我们将利用网络功能，搭建一个 **Web 服务器**，通过手机浏览器直接控制 ESP32 上的灯光或读取传感器数据。

---
