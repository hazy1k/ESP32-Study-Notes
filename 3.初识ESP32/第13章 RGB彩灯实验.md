# 第十三章 RGB彩灯实验

## 1. WS2812B简介

WS2812B 是一款智能控制 LED 光源， 控制电路和 RGB 芯片集成在一个 5050组件的封装中。 内部包括智能数字端口数据锁存器和信号整形放大驱动电路。 其管脚图如下：

![屏幕截图 2024 08 09 101332](https://img.picgo.net/2024/08/09/-2024-08-09-10133200479953f320054b.png)

可将多个 RGB 灯珠级联， 市面上的 RGB 彩灯带也是这样级联的， 如下所示：

![屏幕截图 2024 08 09 101413](https://img.picgo.net/2024/08/09/-2024-08-09-101413b8ee87355d3db7e4.png)

这样 ESP32 只需要通过 1 个 GPIO 口就可以控制数十上百的灯珠。 注意：级联的灯珠越多， 所需电流就越大， 如果数量很多的情况， 建议外接 5V 电源，然后与开发板共 GND 即可。

我们知道颜色是由最基本的三种颜色的不同亮度混合出新颜色。 这 3 个最基本的颜色顺序分别是红， 绿， 蓝（RGB） 。 这里每个颜色的亮度级别从 0-255,0表示没有， 255 表示最亮。 如（255,0,0） 则表示红色最亮。 GPIO 口就是将这些数据逐一发送给 WS2812B RGB 彩灯。

## 2. 硬件设计

本实验使用到硬件资源如下：

- RGB彩灯

- ESP32 GPIO

RGB彩灯电路如下：

![屏幕截图 2024 08 09 101552](https://img.picgo.net/2024/08/09/-2024-08-09-101552ae2051d40f4e5a75.png)

图中已将 WS2812B 级联过程全部封装， 因此没有展示其内部连接， 只提供控制引脚。 由图可知， J2 端子的 WS_DQ 脚为 RGB 彩灯控制口， 可将该引脚与 ESP32的 GPIO 连接。

本章实验使用 ESP32 的 IO16 引脚， 接线如下所示：

![屏幕截图 2024 08 09 101702](https://img.picgo.net/2024/08/09/-2024-08-09-1017028a35f12eaaaa3ce8.png)

## 3. 软件设计

### 3.1 MicroPython函数使用

ESP32 的 MicroPython 固件集成了彩灯驱动模块 NeoPixel， 适用于WS2812B 驱动的灯珠。 因此我们可以直接使用。 说明如下：

![屏幕截图 2024 08 09 101802](https://img.picgo.net/2024/08/09/-2024-08-09-101802d5823a2d7f57a8a1.png)

使用方法如下：

![屏幕截图 2024 08 09 101844](https://img.picgo.net/2024/08/09/-2024-08-09-10184406a0c638db738985.png)

## 3.2 代码分析

```python
from machine import Pin
from neopixel import NeoPixel
import time

# 定义RGB控制对象
# 控制引脚为16，RGB串联5个
pin = 16
rgb_num = 5
rgb_led = NeoPixel(Pin(pin,Pin.OUT),rgb_num)

# 定义RGB颜色
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
INDIGO = (75, 0, 130)
VIOLET = (138, 43, 226)
COLORS = (RED, ORANGE, YELLOW, GREEN, BLUE, INDIGO, VIOLET)

if __name__ == '__main__':
    while True:
        for color in COLORS:
            for i in range(rgb_num):
                rgb_led[i] = (color[0], color[1], color[2])
                rgb_led.write()
                time.sleep_ms(100)
            time.sleep_ms(1000)    


```


