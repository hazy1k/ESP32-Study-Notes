# 第二十五章 WIFI-手机控制LED (Web服务器)

## 1. 导入

在上一章中，我们成功让 ESP32 连接到了路由器，获得了一个局域网 IP 地址。  
本章我们将把 ESP32 变成一个简易的 **Web 服务器 (Web Server)**。  
你不需要开发手机 APP，只需要打开手机浏览器的地址栏，输入 ESP32 的 IP 地址，就能看到一个网页界面，通过点击网页上的按钮来控制 ESP32 上的 LED 灯。

- **技术原理**：Socket 套接字编程（TCP/IP 协议）。
- **交互流程**：
  1. 手机（客户端）发送 HTTP 请求（如 `GET /?led=on`）。
  2. ESP32（服务器）解析请求内容。
  3. ESP32 控制 GPIO 引脚。
  4. ESP32 返回更新后的 HTML 网页给手机。

---

## 2. 硬件准备

- **ESP32 开发板**。
- **LED**：使用板载 LED（通常是 GPIO 2），或者外接一个 LED 到某个引脚。

---

## 3. 核心代码：Socket Web 服务器

为了方便理解，我们将功能封装为一个完整的脚本。这个脚本包含了连接 WiFi 和启动服务器两部分。

**请将以下代码保存为 `main.py` 并运行：**

```python
import network
import socket
import time
from machine import Pin

# --- 配置区域 ---
SSID = "Your_WiFi_Name"      # 修改为你的 WiFi 名称
PASSWORD = "Your_WiFi_Password"  # 修改为你的 WiFi 密码
LED_PIN = 2                  # 板载 LED 通常是 2

# --- 1. 硬件初始化 ---
led = Pin(LED_PIN, Pin.OUT)
led.value(0) # 默认关闭

# --- 2. 连接 WiFi 函数 ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('正在连接 WiFi...')
        wlan.connect(SSID, PASSWORD)
        # 等待连接，超时 10 秒
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > 10:
                print("连接超时！")
                return None
            time.sleep(0.5)

    config = wlan.ifconfig()
    print('WiFi 连接成功!')
    print('IP 地址:', config[0])
    return config[0]

# --- 3. 生成 HTML 网页 ---
# 这是一个简单的 HTML 字符串，包含 CSS 样式让按钮更好看
def get_html(led_status):
    status_text = "ON" if led_status else "OFF"
    color = "green" if led_status else "red"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ESP32 Control</title>
        <style>
            body {{ font-family: Arial; text-align: center; margin-top: 50px; }}
            h1 {{ color: #333; }}
            .btn {{ 
                display: inline-block; 
                padding: 15px 30px; 
                font-size: 24px; 
                color: white; 
                background-color: {color}; 
                border: none; 
                border-radius: 10px; 
                text-decoration: none; 
                box-shadow: 2px 2px 5px #888;
            }}
            .btn:active {{ box-shadow: none; transform: translateY(2px); }}
        </style>
    </head>
    <body>
        <h1>ESP32 LED Control</h1>
        <p>Current Status: <strong>{status_text}</strong></p>
        <p>
            <a class="btn" href="/?led=on">Turn ON</a>
            <a class="btn" href="/?led=off" style="background-color: grey;">Turn OFF</a>
        </p>
    </body>
    </html>
    """
    return html

# --- 4. 启动 Web 服务器 ---
def start_server(ip):
    # 创建 TCP Socket
    # AF_INET: IPv4, SOCK_STREAM: TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 绑定地址和端口 (80 是 HTTP 默认端口)
    # setblocking(False) 或 SO_REUSEADDR 可以防止"地址被占用"错误
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5) # 开始监听，最大连接数 5

    print(f"Web 服务器已启动，请在手机浏览器访问: http://{ip}")

    while True:
        try:
            # 阻塞等待客户端连接
            conn, addr = s.accept()
            print('收到连接来自:', addr)

            # 接收请求数据 (最大 1024 字节)
            request = conn.recv(1024)
            request = str(request)
            # print('请求内容:', request) # 调试用，可以打印看看

            # --- 解析请求 ---
            # 查找 URL 中是否包含控制命令
            led_on = request.find('/?led=on')
            led_off = request.find('/?led=off')

            if led_on == 6: # GET /?led=on ...
                print('LED ON')
                led.value(1)
            if led_off == 6:
                print('LED OFF')
                led.value(0)

            # --- 发送响应 ---
            # 1. HTTP 响应头
            response_headers = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
            # 2. HTML 内容
            response_body = get_html(led.value())

            conn.send(response_headers)
            conn.send(response_body)

            # 关闭连接
            conn.close()

        except OSError as e:
            conn.close()
            print('Connection closed error:', e)

# --- 主程序入口 ---
try:
    ip_address = connect_wifi()
    if ip_address:
        start_server(ip_address)
except KeyboardInterrupt:
    print("程序停止")
```

---

## 4. 操作步骤

1. **修改代码**：将代码中的 `SSID` 和 `PASSWORD` 修改为你路由器的真实信息。
2. **运行程序**：在 Thonny 中运行代码。
3. **查看 Shell**：等待连接成功，Shell 窗口会打印出 IP 地址，例如 `192.168.1.105`。
4. **手机控制**：
   - 确保手机连接在**同一个 WiFi** 下。
   - 打开手机浏览器（Safari, Chrome 等）。
   - 在地址栏输入 IP 地址（如 `192.168.1.105`）并访问。
   - 你将看到一个网页，点击绿色的 **Turn ON** 或灰色的 **Turn OFF** 按钮，观察 ESP32 上的 LED 灯是否变化。

---

## 5. 代码解析

- **`socket.bind(('', 80))`**：
  - `''` 表示绑定本机所有可用 IP。
  - `80` 是 HTTP 协议的标准端口，这样你在浏览器输入 IP 时不需要加端口号（如果是 8080 端口，则需输入 `192.168.1.105:8080`）。
- **解析逻辑**：
  - 当你在浏览器点击按钮时，浏览器会向 ESP32 发送类似 `GET /?led=on HTTP/1.1` 的请求。
  - 代码通过 `request.find('/?led=on')` 查找字符串。如果找到了，就执行 `led.value(1)`。
- **`get_html()`**：
  - 这里使用了 Python 的 **f-string**，根据当前 `led.value()` 的状态，动态生成 HTML。如果灯是开的，网页上的状态文字就显示 "ON"，否则显示 "OFF"。这让网页有了“状态反馈”。

---

## 6. 常见问题

1. **OSError: [Errno 98] EADDRINUSE**：
   - **原因**：你停止程序后立刻再次运行，端口 80 还没被操作系统释放。
   - **解决**：代码中加入了 `s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)` 可以极大缓解此问题。如果还是报错，请执行一下 `Soft Reset` (Ctrl+D) 或按 ESP32 复位键。
2. **手机打不开网页**：
   - 确保手机和 ESP32 连的是**同一个路由器**。
   - 部分公司或学校网络会通过防火墙禁止局域网设备互访（AP 隔离），请尝试用手机开热点给 ESP32 连接测试。
3. **反应慢**：
   - 由于是单线程阻塞模式，一次只能处理一个请求。如果你狂点按钮，或者有多个人同时访问，ESP32 可能会响应不过来。

## 7. 小结

本章通过最基础的 Socket 编程实现了一个 B/S 架构（浏览器/服务器）的控制系统。

- **优点**：无需安装任何 APP，跨平台（安卓、iOS、电脑都能用）。
- **缺点**：这种阻塞式的 Socket 写法在处理复杂逻辑时会卡顿。
- **进阶方向**：为了实现更复杂的 Web 功能（如异步处理、更漂亮的界面），在 Python 开发中通常会使用轻量级 Web 框架，如 **Microdot**。但对于简单的点灯和传数据，本章的方法已经足够好用。

下一章，我们将尝试连接 **MQTT 服务器**，实现真正的远程控制（哪怕手机用 5G 也能控制家里的 ESP32）。

---
