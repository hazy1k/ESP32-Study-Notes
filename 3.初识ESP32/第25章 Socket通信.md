# 第二十五章 Socket通信

## 1. 导入

Socket 我们听得非常多了， 但由于网络工程是一门系统工程， 涉及的知识非常广， 概念也很多， 任何一个知识点都能找出一堆厚厚的的书， 因此我们经常会混淆。 在这里， 我们尝试以最容易理解的方式来讲述 Socket， 如果需要全面了解， 可以自行查阅相关资料学习。

我们先来看看网络层级模型图， 这是构成网络通信的基础：

![](C:\Users\qiu\AppData\Roaming\marktext\images\2024-08-16-09-51-16-image.png)

我们看看 TCP/IP 模型的传输层和应用层， 传输层比较熟悉的概念是 TCP和 UDP， UPD 协议基本没有对 IP 层的数据进行任何的处理了。 而 TCP 协议还加入了更加复杂的传输控制， 比如滑动的数据发送窗口（Slice Window） ， 以及接收确认和重发机制， 以达到数据的可靠传送。 应用层中网页常用的则是 HTTP。那么我们先来解析一下这 TCP 和 HTTP 两者的关系。

我们知道网络通信是最基础是依赖于 IP 和端口的， HTTP 一般情况下默认使用端口 80。 举个简单的例子： 我们逛淘宝， 浏览器会向淘宝网的网址（本质是 IP） 和端口发起请求， 而淘宝网收到请求后响应， 向我们手机返回相关网页数据信息， 实现了网页交互的过程。 而这里就会引出一个多人连接的问题， 很多人访问淘宝网， 实际上接收到网页信息后就断开连接， 否则淘宝网的服务器是无法支撑这么多人长时间的连接的， 哪怕能支持， 也非常占资源。

也就是应用层的 HTTP 通过传输层进行数据通信时， TCP 会遇到同时为多个应用程序进程提供并发服务的问题。 多个 TCP 连接或多个应用程序进程可能需要通过同一个 TCP 协议端口传输数据。 为了区别不同的应用程序进程和连接，许多计算机操作系统为应用程序与 TCP／ IP 协议交互提供了套接字(Socket)接口。 应用层可以和传输层通过 Socket 接口， 区分来自不同应用程序进程或网络连接的通信， 实现数据传输的并发服务。

简单来说， Socket 抽象层介于传输层和应用层之间， 跟 TCP/IP 并没有必然的联系。 Socket 编程接口在设计的时候， 就希望也能适应其他的网络协议。

![屏幕截图 2024 08 16 094912](https://img.picgo.net/2024/08/16/-2024-08-16-0949129ab7c5be101808a6.png)

![](C:\Users\qiu\AppData\Roaming\marktext\images\2024-08-16-09-51-55-image.png)

套接字（socket） 是通信的基石， 是支持 TCP/IP 协议的网络通信的基本操作单元。 它是网络通信过程中端点的抽象表示， 包含进行网络通信必须的五种信息： 连接使用的协议（通常是 TCP 或 UDP） ， 本地主机的 IP 地址， 本地进程的协议端口， 远地主机的 IP 地址， 远地进程的协议端口。

所以， socket 的出现只是可以更方便的使用 TCP/IP 协议栈而已， 简单理解就是其对 TCP/IP 进行了抽象， 形成了几个最基本的函数接口。 比如 create， listen， accept， connect， read 和 write 等等。 以下是通讯流程：

![屏幕截图 2024 08 16 094956](https://img.picgo.net/2024/08/16/-2024-08-16-094956132b84796ecf0730.png)

从上图可以看到， 建立 Socket 通信需要一个服务器端和一个客户端， 以本实验为例， ESP32 开发板作为客户端， 电脑使用网络调试助手作为服务器端， 双方使用 TCP 协议传输。 对于客户端， 则需要知道电脑端的 IP 和端口即可建立连接。（端口可以自定义， 范围在 0~65535， 注意不占用常用的 80 等端口即可。）

以上的内容， 简单来说就是如果用户面向应用来说， 那么 ESP32 只需要知道通讯协议是 TCP 或 UDP、 服务器的 IP 和端口号这 3 个信息， 即可向服务器发起连接和发送信息。

## 2. 硬件设计

由于 ESP32 内置 WIFI 功能， 所以直接在开发板上使用即可， 无需额外连接。

## 3. 软件设计

### 3.1 MicroPython函数使用

MicroPython 已经封装好相关模块 usocket,它与传统的 socket 大部分兼容， 两者均可使用， 本实验使用 usocket， 对象如下介绍：

![](C:\Users\qiu\AppData\Roaming\marktext\images\2024-08-16-09-53-25-image.png)

### 3.2 代码分析

```py
from machine import Pin
import time, network, usocket

led1 = Pin(15, Pin.OUT)

ssid = "ssid"
password = "12345678"

dest_ip = "192.168.103.148"
dest_port = 10000

# WIFI连接
def wifi_connect():
    wlan = network.WLAN(network.STA_IF) # STA模式
    wlan.active(True) # 激活接口
    start_time = time.time() # 记录开始时间

    if not wlan.isconnected(): # 如果没有连接过WIFI
        print("WIFI connecting...")
        wlan.connect(ssid, password) # 连接WIFI

        while not wlan.isconnected(): # 等待连接
            led1.value(1)
            time.sleep_ms(500)
            led1.value(0)
            time.sleep_ms(500)

        # 超时判断
            if time.time() - start_time > 15:
                print("WIFI connect timeout!")
                break

    else:
        led1.value(0)
        print("network information:", wlan.ifconfig()) # 打印IP信息    

if __name__ == "__main__":
    if wifi_connect():
        socket = usocket.socket() # 创建socket连接
        addr = (dest_ip, dest_port) # 服务器IP地址和端口
        socket.connect(addr) # 连接服务器
        socket.send("Hello, server!") # 发送数据

        while True:
            text = socket.recv(128) # 接收数据
            if text == None:
                pass
            else:
                print(text) # 打印接收到的数据
                socket.send("I received: " + text.decode("utf-8")) # 发送数据
            time.sleep_ms(100) # 延时100ms
```

---

2024.8.24 第一次修订，后期不再维护
