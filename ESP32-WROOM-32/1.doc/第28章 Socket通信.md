# 第二十八章 Socket通信 (TCP/UDP)

## 1. 导入

在第25章中，我们写了一个 Web 服务器，它其实就是建立在 **TCP Socket** 之上的。Web 服务器必须遵守 HTTP 协议（发送 Header、Body 等），而 **Raw Socket (原始套接字)** 通信则更加自由。

你可以自定义协议（比如发送字符串 "LED_ON" 而不是复杂的 HTTP 请求），这在工业控制、实时数据传输（如音频流、机械臂控制）中非常常用。

Socket 通信主要分为两种模式：

1. **TCP (传输控制协议)**：像打电话。必须先建立连接，数据保证送达，顺序不乱。可靠，但稍微慢一点。
2. **UDP (用户数据报协议)**：像寄信/广播。不需要建立连接，直接发。快，但不保证送达（可能会丢包）。

---

## 2. 必备工具

为了测试 Socket 通信，你需要一个“调试助手”运行在电脑上，充当服务器或客户端。

- **推荐软件**：**NetAssist (网络调试助手)**。
- **替代方案**：使用 Python 在电脑上写个简单的脚本。

---

## 3. 模式一：ESP32 作为 TCP Server (服务端)

**场景**：ESP32 在家里“坐着”，电脑连接 ESP32，发送指令控制它。这是最常用的局域网控制方式。

```python
import network
import socket
import time
from machine import Pin

# --- 配置 ---
SSID = "Your_WiFi_Name"
PASS = "Your_WiFi_Password"
PORT = 8080 # 监听端口 (建议 > 1024)

# LED 初始化
led = Pin(2, Pin.OUT)

# 1. 联网
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
while not wlan.isconnected():
    time.sleep(0.5)
    print(".", end="")
my_ip = wlan.ifconfig()[0]
print(f"\nWiFi Connected! IP: {my_ip}")

def start_tcp_server():
    # 2. 创建 Socket (AF_INET=IPv4, SOCK_STREAM=TCP)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 允许地址重用 (避免停止程序后端口被占用报错)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # 绑定 IP 和 端口
    try:
        s.bind(('', PORT))
    except OSError as e:
        print("端口绑定失败，请重启设备")
        return

    s.listen(1) # 开始监听，参数为允许排队的最大连接数
    print(f"TCP Server 正在监听: {my_ip}:{PORT}")

    while True:
        try:
            print("等待客户端连接...")
            # 阻塞等待，直到有客户端连上来
            conn, addr = s.accept() 
            print(f"客户端已连接: {addr}")
            
            # 保持连接的循环
            while True:
                # 接收数据 (缓冲区 1024 字节)
                data = conn.recv(1024)
                
                # 如果 data 为空，说明客户端主动断开了连接
                if not data:
                    print("客户端断开连接")
                    break
                
                # 解码并处理
                msg = data.decode().strip() # 去除回车换行
                print(f"收到: {msg}")
                
                # 业务逻辑
                if msg == "on":
                    led.value(1)
                    conn.send(b"LED is ON\n")
                elif msg == "off":
                    led.value(0)
                    conn.send(b"LED is OFF\n")
                else:
                    conn.send(f"Unknown command: {msg}\n".encode())
            
            # 跳出内层循环后，关闭这个连接，回到外层继续等待新连接
            conn.close()
            
        except OSError as e:
            print("连接异常:", e)
            conn.close()

# 运行
start_tcp_server()
```

**测试方法**：

1. 电脑打开“网络调试助手”。
2. 协议选择 **TCP Client**。
3. 远程主机 IP 填 ESP32 的 IP，端口填 `8080`。
4. 点击连接，发送 `on` 或 `off`。

---

## 4. 模式二：ESP32 作为 TCP Client (客户端)

**场景**：ESP32 主动把采集到的温湿度数据发送给电脑上的服务器。

**注意**：测试前请查询你**电脑的局域网 IP** (Windows 终端输入 `ipconfig`)，并确保电脑防火墙允许端口通过。

```python
import network
import socket
import time

# --- 配置 ---
SERVER_IP = "192.168.1.5" # 【重要】修改为你电脑的 IP
SERVER_PORT = 6000        # 电脑端调试助手监听的端口

# 联网代码 (略，同上，确保已连接)
# ...

def start_tcp_client():
    # 创建 Socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 设置超时时间 (例如 5秒)，防止连不上一直卡死
    s.settimeout(5)
    
    try:
        print(f"正在连接服务器 {SERVER_IP}:{SERVER_PORT} ...")
        s.connect((SERVER_IP, SERVER_PORT))
        print("连接成功！")
        
        while True:
            # 模拟发送数据
            msg = f"Temp: 25.5, Time: {time.ticks_ms()}\n"
            s.send(msg.encode())
            print("已发送:", msg.strip())
            
            # 也可以接收服务器的回信
            # response = s.recv(1024)
            # print("收到回信:", response)
            
            time.sleep(2)
            
    except OSError as e:
        print("连接失败或断开:", e)
    finally:
        s.close()
        print("Socket 已关闭")

# 运行
# start_tcp_client() 
```

**测试方法**：

1. 电脑打开“网络调试助手”。
2. 协议选择 **TCP Server**。
3. 本地端口填 `6000`，点击打开。
4. 运行 ESP32 代码，电脑端应能收到数据。

---

## 5. 模式三：UDP 通信 (广播/快速传输)

**场景**：不需要建立连接，直接把数据“扔”出去。常用于 LED 灯带同步、实时音频，或者还没配网时广播“我在这里”。

```python
import socket
import time

# UDP 不需要 listen，也不需要 connect
# SOCK_DGRAM 代表 UDP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 绑定本地端口 (接收用)
try:
    s.bind(('', 7777))
except:
    print("端口绑定失败")

TARGET_IP = "192.168.1.5" # 目标电脑 IP
TARGET_PORT = 8888        # 目标电脑 UDP 端口

print("UDP 模式启动...")

# 使用非阻塞模式，防止 recvfrom 卡死程序
s.setblocking(False) 

while True:
    try:
        # 1. 发送数据 (sendto 需要指定地址)
        msg = b"Hello via UDP"
        s.sendto(msg, (TARGET_IP, TARGET_PORT))
        
        # 2. 接收数据 (如果有的话)
        try:
            data, addr = s.recvfrom(1024)
            print(f"收到来自 {addr} 的 UDP 包: {data}")
        except OSError:
            # 在非阻塞模式下，如果没有数据会报错，忽略即可
            pass
            
        time.sleep(1)
        
    except Exception as e:
        print("Error:", e)
        time.sleep(1)
```

---

## 6. 关键知识点与“坑”

1. **阻塞 (Blocking) vs 非阻塞**：
   
   - `s.accept()` 和 `s.recv()` 默认是**阻塞**的。也就是说，如果没有人连接或者没有收到数据，程序会**停在这一行不动**，LED 灯也不会闪烁。
   - **解决**：
     - 简单法：使用 `s.settimeout(1.0)` 设置超时。
     - 进阶法：使用 `s.setblocking(False)`，然后用 `try-except` 捕获异常。
     - 高级法：使用 `select` 模块或 `uasyncio` (MicroPython 的异步库)。

2. **地址重用错误 (EADDRINUSE)**：
   
   - 当你停止程序并立即重新运行时，经常报错 `OSError: [Errno 98] EADDRINUSE`。
   - 这是因为 TCP 连接关闭后会保留一段时间状态。
   - **必加代码**：`s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)`。

3. **心跳包 (Keepalive)**：
   
   - 在 TCP 长连接中，如果网线断了，双方可能不知道。建议每隔一段时间发送一个简单的“心跳包”来确认连接存活。

4. **粘包 (TCP only)**：
   
   - TCP 是流式协议。你发送两次 "Hello"，接收端可能一次性收到 "HelloHello"。
   - **解决**：在消息末尾加换行符 `\n`，接收端按行读取；或者规定固定长度。

## 7. 小结

Socket 是网络编程的基石。

- **控制指令**：首选 **TCP Server** (ESP32) + 手机/电脑 Client。
- **数据上传**：首选 **TCP Client** (ESP32) + 电脑 Server。
- **发现设备/即时控制**：使用 **UDP**。

---
