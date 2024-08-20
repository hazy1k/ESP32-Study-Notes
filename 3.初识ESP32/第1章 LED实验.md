# 第一章 LED实验

## 1. 导入

相信大部分人开始学习嵌入式单片机编程时都会从点亮 LED 开始， 我们在学习 ESP32 使用 MicroPython 的编程也不例外， 通过点亮第一个 LED 能让你对编译环境和程序架构有一定的认识， 为以后的学习和更大型的程序打下基础， 增加信心。

## 2. 硬件设计

本实验使用到硬件资源如下： 

- LED 模块中 D1 指示

- ESP32 GPIO

LED 模块电路如下所示：

![屏幕截图 2024 08 02 172220](https://img.picgo.net/2024/08/02/-2024-08-02-17222055dc03663a6bf9ed.png)

由图可知， J1 端子为 LED 的控制端， 要使 LED 点亮， 只需给 J1 端子一个高电平， 因此可使用导线将 ESP32 的 IO 口与 J1 端子连接， 通过 ESP32 的 GPIO 输出高电平即可控制 LED 点亮。

本章实验使用 ESP32 的 IO15,2,0,4,16,17,5,18 引脚， 接线如下所示：

![屏幕截图 2024 08 02 172340](https://img.picgo.net/2024/08/02/-2024-08-02-172340dd87742e7d2fe6aa.png)

接线说明：

```c
LED 模块-->ESP32 IO
(D1-D8)-->(15,2,0,4,16,17,5,18)
```

## 2. 软件设计

### 2.1 实验目的

点亮led模块中的一个led灯

### 2.2 Micropython函数介绍

MicroPython 中可使用 machine 模块中的 Pin 模块对 GPIO 输出控制。 其构造方法和使用方法如下：

![屏幕截图 2024 08 02 172611](https://img.picgo.net/2024/08/02/-2024-08-02-172611a89b766a27a65af0.png)

图中对 MicroPython 的 machine 中 Pin 对象做了详细的说明， machine是大模块， Pin 是 machine 下面的一个小模块， 在 python 编程里有两种方式引用相关模块：

方式 1 是： import machine， 然后通过 machine.Pin 来操作；

方式 2 是： from machine import Pin， 意思是直接从 machine 中引入 Pin模块， 然后直接通过构建 led 对象来操作。 本章实验中使用方式 2 导入模块，代码更直观方便。

Pin 模块的使用方法如下：

![屏幕截图 2024 08 02 172801](https://img.picgo.net/2024/08/02/-2024-08-02-172801fed3806a0326228a.png)

### 2.3 正式点亮我们的第一个led啦

```python
from machine import Pin

led1 = Pin(15, Pin.OUT)
led1.value(1)
```

## 3. 小结

这一节很简单，没什么可说的，会用from machine import Pin就行，相比stm32简单太多了，这就python的魅力！语法简单，清晰明了

---

2024.8.20 第一次修订，后期不再维护
