# 第二十四章 WIFI实验-连接路由器

## 1. 导入

WIFI 是物联网中非常重要的角色， 现在基本上家家户户都有 WIFI 网络，通过 WIFI 接入到互联网， 成了智能家居产品普遍的选择。 而要想上网， 首先需要连接上无线路由器。 本章我们就来学习如何通过 MicroPython 编程连上路由器。

连接路由器上网是我们每天都做的事情， 日常生活中我们只需要知道路由器的账号和密码， 就能使用电脑或者手机连接到无线路由器， 然后上网冲浪。

## 2. 硬件设计

由于 ESP32 内置 WIFI 功能， 所以直接在开发板上使用即可， 无需额外连接。

## 3. 软件设计

### 3.1 MicroPython函数使用

MicroPython 已经集成了 network 模块， 开发者使用内置的 network 模块函数可以非常方便地连接上路由器。 但往往也有各种连接失败的情况， 如密码不正确等。 这时我们只需再加上一些简单的判断机制， 避免陷入连接失败的死循环即可。 我们先来看看 network 基于 WiFi（WLAN 模块） 的构造函数和使用方法。

![屏幕截图 2024 08 15 100903](https://img.picgo.net/2024/08/15/-2024-08-15-1009031910b4a3e75d8229.png)

模块包含热点 AP 模式和客户端 STA 模式， 热点 AP 是指电脑或手机端直接连接 ESP32 发出的热点实现连接， 如果电脑连接模块 AP 热点， 这样电脑就不能上网， 因此在使用电脑端和模块进行网络通信时， 一般情况下都是使用 STA 模式。 也就是电脑和设备同时连接到相同网段的路由器上。

使用方法如下：

![屏幕截图 2024 08 16 092242](https://img.picgo.net/2024/08/16/-2024-08-16-0922428110d3d920740dfa.png)

![](C:\Users\qiu\AppData\Roaming\marktext\images\2024-08-16-09-32-10-image.png)

### 3.2 代码分析

```python
from machine import Pin
import time
import network

led1 = Pin(15, Pin.OUT)

# 路由器账号密码
ssid = "ssid"
password = "12345678"

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
    wifi_connect() # 连接WIFI
```

---

2024.8.24 第一次修订，后期不再维护
