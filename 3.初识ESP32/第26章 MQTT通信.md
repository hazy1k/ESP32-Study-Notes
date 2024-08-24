# 第二十六章 MQTT通信

## 1. MQTT简介

QTT 是 IBM 于 1999 年提出的， 和 HTTP 一样属于应用层， 它工作在TCP/IP 协议族上， 通常还会调用 socket 接口。 是一个基于客户端-服务器的消息发布/订阅传输协议。 其特点是协议是轻量、 简单、 开放和易于实现的， 这些特点使它适用范围非常广泛。 在很多情况下， 包括受限的环境中， 如： 机器与机器（M2M） 通信和物联网（IoT） 。 其在通过卫星链路通信传感器、 偶尔拨号的医疗设备、 智能家居、 及一些小型化设备中已广泛使用。

总结下来 MQTT 有如下特性/优势：

- 异步消息协议

- 面向长连接

- 双向数据传输

- 协议轻量级

- 被动数据获取

![屏幕截图 2024 08 17 090751](https://img.picgo.net/2024/08/17/-2024-08-17-090751a4c888df75060c59.png)

从上图可看到， MQTT 通信的角色有两个， 分别是服务器和客户端。 服务器只负责中转数据， 不做存储； 客户端可以是信息发送者或订阅者， 也可以同时是两者。 具体如下图：

![](C:\Users\qiu\AppData\Roaming\marktext\images\2024-08-17-09-09-09-image.png)

确定了角色后， 数据是如何传输的呢？ 下图是 MQTT 最基本的数据帧格式，例如温度传感器发布主题“Temperature” 编号,消息是“25” （表示温度） 。 那么所有订阅了这个主题编号的客户端（手机应用） 就会收到相关信息， 从而实现通信。

![](C:\Users\qiu\AppData\Roaming\marktext\images\2024-08-17-09-09-54-image.png)

由于特殊的发布/订阅机制， 服务器不需要存储数据（当然也可以在服务器的设备上建立一个客户端来订阅保存信息） ， 因此非常适合海量设备的传输。

## 2. 硬件设计

由于 ESP32 内置 WIFI 功能， 所以直接在开发板上使用即可， 无需额外连接。

## 3. 软件设计

### 3.1 MicroPython函数使用

MicroPython 已经封装好 MQTT 客户端模块,这使得 MQTT 应用开发变得简单。MQTT 模块文件在例程文件夹里面的 simple.py 文件， 使用方法如下：

![](C:\Users\qiu\AppData\Roaming\marktext\images\2024-08-17-09-10-45-image.png)

### 3.2 代码分析

由于客户端分为发布者和订阅者角色， 因此为了方便大家更好理解， 本实验分开两个程序来编程， 分别为发布者和订阅者。

#### 3.2.1 发布者

```python
#导入Pin模块
from machine import Pin
import time
from machine import Timer
import network
from simple import MQTTClient

#定义LED控制对象
led1=Pin(15,Pin.OUT)

#路由器WIFI账号和密码
ssid="ssid"
password="12345678"

#WIFI连接
def wifi_connect():
    wlan=network.WLAN(network.STA_IF)  #STA模式
    wlan.active(True)  #激活
    start_time=time.time()  #记录时间做超时判断

    if not wlan.isconnected():
        print("conneting to network...")
        wlan.connect(ssid,password)  #输入WIFI账号和密码

        while not wlan.isconnected():
            led1.value(1)
            time.sleep_ms(300)
            led1.value(0)
            time.sleep_ms(300)

            #超时判断,15 秒没连接成功判定为超时
            if time.time()-start_time>150:
                print("WIFI Connect Timeout!")
                break
        return False

    else:
        led1.value(0)
        print("network information:", wlan.ifconfig())
        return True

#发布数据任务
def mqtt_send(tim):
    client.publish(TOPIC, "Hello PRECHIN")

#程序入口
if __name__=="__main__":

    if wifi_connect():
        SERVER="mq.tongxinmao.com"
        PORT=18830
        CLIENT_ID="PZ-ESP32"  #客户端ID
        TOPIC="/public/pz_esp32/1"  #TOPIC名称
        client = MQTTClient(CLIENT_ID, SERVER, PORT)
        client.connect()

        #开启RTOS定时器,周期 1000ms，执行MQTT通信接收任务
        tim = Timer(0)
        tim.init(period=1000, mode=Timer.PERIODIC,callback=mqtt_send)
```

### 3.2.2 订阅者

```python
#导入Pin模块
from machine import Pin
from machine import Timer
import time
import network
from simple import MQTTClient

#定义LED控制对象
led1=Pin(15,Pin.OUT)

#路由器WIFI账号和密码
ssid="ssid"
password="12345678"

#WIFI连接
def wifi_connect():
    wlan=network.WLAN(network.STA_IF)  #STA模式
    wlan.active(True)  #激活
    start_time=time.time() # 记录时间做超时判断

    if not wlan.isconnected():
        print("conneting to network...")
        wlan.connect(ssid,password)  #输入WIFI账号和密码

        while not wlan.isconnected():
            led1.value(1)
            time.sleep_ms(300)
            led1.value(0)
            time.sleep_ms(300)

            #超时判断,15 秒没连接成功判定为超时
            if time.time()-start_time>150:
                print("WIFI Connect Timeout!")
                break
        return False

    else:
        led1.value(0)
        print("network information:", wlan.ifconfig())
        return True

#设置 MQTT 回调函数,有信息时候执行
def mqtt_callback(topic,msg):
    print("topic: {}".format(topic))
    print("msg: {}".format(msg))

#接收数据任务
def mqtt_recv(tim):
    client.check_msg()


#程序入口
if __name__=="__main__":

    if wifi_connect():
        SERVER="mq.tongxinmao.com"
        PORT=18830
        CLIENT_ID="PZ-ESP32"  #客户端ID
        TOPIC="/public/pz_esp32/1"  #TOPIC名称
        client = MQTTClient(CLIENT_ID, SERVER, PORT)  #建立客户端
        client.set_callback(mqtt_callback)  #配置回调函数
        client.connect()
        client.subscribe(TOPIC)  #订阅主题

        #开启RTOS定时器,周期 300ms，执行MQTT通信接收任务
        tim = Timer(0)
        tim.init(period=300, mode=Timer.PERIODIC,callback=mqtt_recv)
```

---

2024.8.24 第一次修订，后期不再维护
