# 第二十六章 MQTT通信 (物联网核心协议)

## 1. 导入

上一章我们用 Socket 实现了“局域网”内的控制。但如果你想在公司控制家里的灯，或者让设备把数据上传到云端大屏，Socket 就很难办了（需要公网 IP 或内网穿透）。

**MQTT (Message Queuing Telemetry Transport)** 是为物联网设计的轻量级协议。它不使用“请求-响应”模式，而是使用 **“发布-订阅” (Publish/Subscribe)** 模式。

- **核心优势**：
  - **极其省流**：报头极小，适合带宽有限的网络。
  - **双向通信**：设备既能发数据（发布），也能收指令（订阅）。
  - **解耦**：设备不需要知道谁在听，只需要往“主题”里发消息即可。

---

## 2. 核心概念

1. **Broker (代理/服务器)**：邮局。负责接收和转发消息（如 EMQX, Mosquitto, 阿里云 IoT）。
2. **Topic (主题)**：信箱地址。例如 `home/livingroom/light`。支持层级，用 `/` 分隔。
3. **Payload (消息体)**：信件内容。例如 `on`, `off`, `{"temp": 25}`。
4. **Publish (发布)**：投递信件。
5. **Subscribe (订阅)**：关注某个信箱，一旦有新信件，Broker 会立刻推送到你手里。

---

## 3. 准备工作

- **库**：MicroPython 官方固件通常内置了 `umqtt.simple` 库。
- **测试服务器**：我们将使用免费的公共 MQTT 测试服务器（EMQX 提供）。
  - **地址**：`broker.emqx.io`
  - **端口**：`1883` (TCP)
- **电脑端调试工具**：推荐下载安装 **MQTTX** 软件，或者使用在线版，用于模拟手机端收发数据。

---

## 4. 完整实战代码

我们将实现一个**双向通信**的例子：

1. **上报**：ESP32 每隔 5 秒向 `esp32/sensor` 主题发送运行时间。
2. **控制**：ESP32 订阅 `esp32/led` 主题，收到 `on` 开灯，收到 `off` 关灯。

**注意**：代码中使用了**非阻塞**写法，这是 MQTT 稳定运行的关键。

```python
import network
import time
from machine import Pin
from umqtt.simple import MQTTClient

# --- 1. 配置参数 ---
WIFI_SSID = "Your_WiFi_Name"     # WiFi 名称
WIFI_PASS = "Your_WiFi_Password" # WiFi 密码

# MQTT 服务器配置 (这里使用 EMQX 免费公共服务器)
MQTT_SERVER = "broker.emqx.io"
MQTT_PORT   = 1883
# 客户端 ID 必须唯一，否则会互相挤下线
MQTT_CLIENT_ID = "esp32_demo_" + str(time.time()) 

# 主题定义 (建议加上随机后缀防止和别人的测试冲突)
TOPIC_PUB = b"esp32/sensor"   # 发布主题：上传数据
TOPIC_SUB = b"esp32/led"      # 订阅主题：接收控制指令

# --- 2. 硬件初始化 ---
led = Pin(2, Pin.OUT) # 板载 LED
led.value(0)

# --- 3. 连接 WiFi ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('正在连接 WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
            print(".", end="")
    print('\nWiFi 已连接, IP:', wlan.ifconfig()[0])

# --- 4. MQTT 回调函数 (收到消息时触发) ---
def sub_cb(topic, msg):
    print(f"\n收到来自 [{topic.decode()}] 的消息: {msg.decode()}")

    # 根据消息内容控制 LED
    if msg == b"on":
        led.value(1)
        print("--> 开灯")
    elif msg == b"off":
        led.value(0)
        print("--> 关灯")
    else:
        print("--> 未知指令")

# --- 5. MQTT 连接与主循环 ---
def main():
    connect_wifi()

    print(f"正在连接 MQTT 服务器: {MQTT_SERVER} ...")
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, port=MQTT_PORT)

    # 注册回调函数 (要在 connect 之前)
    client.set_callback(sub_cb)
    client.connect()
    print("MQTT 连接成功!")

    # 订阅主题
    client.subscribe(TOPIC_SUB)
    print(f"已订阅主题: {TOPIC_SUB.decode()}")

    # 计时变量
    last_pub_time = 0

    try:
        while True:
            # A. 检查是否有新消息 (非常重要!)
            # check_msg 是非阻塞的，如果有消息会触发 sub_cb，没消息直接通过
            client.check_msg()

            # B. 定时发布数据 (每 5 秒)
            now = time.time()
            if now - last_pub_time >= 5:
                # 构造消息
                msg = f"Uptime: {now} s"
                # 发布消息
                client.publish(TOPIC_PUB, msg)
                print(f"已发布: {msg} -> {TOPIC_PUB.decode()}")

                last_pub_time = now

            # 避免 CPU 占用过高，稍微睡一小会儿
            time.sleep_ms(100)

    except OSError as e:
        print("发生错误 (网络断开?):", e)
        # 实际项目中这里应该添加重连机制
        client.disconnect()

# --- 运行 ---
if __name__ == "__main__":
    main()
```

---

## 5. 验证步骤 (配合 MQTTX)

光有代码不行，你需要一个“遥控器”来测试。

1. **下载软件**：在电脑安装 [MQTTX](https://mqttx.app/zh) (开源免费)。
2. **建立连接**：
   - 打开 MQTTX，点击 `+` 新建连接。
   - Name: 随意 (如 TestPC)。
   - Host: `broker.emqx.io`
   - Port: `1883`
   - 点击 **Connect**，右上角变绿表示连接成功。
3. **订阅 (收数据)**：
   - 点击 **Add Subscription**。
   - Topic: `esp32/sensor` (要和代码里的 `TOPIC_PUB` 一致)。
   - 点击 Confirm。
   - **现象**：你应该能看到电脑上每隔 5 秒弹出一个 `Uptime: xxx s` 的消息。
4. **发布 (发指令)**：
   - 在下方的发送栏。
   - Topic: `esp32/led` (要和代码里的 `TOPIC_SUB` 一致)。
   - Payload: 输入 `on`。
   - 点击发送图标。
   - **现象**：观察你的 ESP32 开发板，LED 灯应该亮起，且 Thonny 控制台打印 `--> 开灯`。发送 `off` 则熄灭。

---

## 6. 常见问题与“坑”

1. **阻塞问题 (`wait_msg` vs `check_msg`)**：
   - 有些教程使用 `client.wait_msg()`，这会**阻塞**程序，直到收到下一条消息。如果不发消息，ESP32 就卡死在那里，无法执行定时任务（如传感器读取）。
   - **务必使用** `client.check_msg()` 配合循环，这是实现多任务的基础。
2. **KeepAlive 掉线**：
   - MQTT 连接有一个 `keepalive` 参数（默认 60秒）。如果 ESP32 超过 60秒 既不发消息也不回 Ping，服务器会踢掉它。
   - `client.check_msg()` 内部会自动处理 Ping 包，所以只要循环还在跑，通常不会掉线。
3. **QoS (服务质量)**：
   - `umqtt.simple` 默认 QoS=0 (发出去就不管了，不可靠)。
   - 如果需要 QoS=1 (保证至少送达一次)，需要使用 `umqtt.robust` 库，逻辑会稍微复杂一点（涉及自动重连）。
4. **字节串 (`bytes`)**：
   - 注意回调函数里的 `topic` 和 `msg` 都是 `bytes` 类型（如 `b'on'`）。
   - 对比字符串时，要么写 `if msg == b"on":`，要么先解码 `msg.decode() == "on"`。

## 7. 小结

本章你掌握了物联网最通用的 **MQTT 协议**。  
现在，你的 ESP32 不再是一个孤岛，它已经连入了全球互联网。

- **上行**：你可以把温度、湿度传到云端数据库。
- **下行**：你可以在地球任何有网络的地方，控制家里的设备。

---
