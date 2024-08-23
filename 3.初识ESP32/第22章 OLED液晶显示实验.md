# 第二十二章 OLED液晶显示实验

## 1. OLED介绍

LED， 即有机发光二极管（ Organic Light Emitting Diode） 。 OLED 由于同时具备自发光， 不需背光源、 对比度高、 厚度薄、 视角广、 反应速度快、 可用于挠曲性面板、 使用温度范围广、 构造及制程较简单等优异之特性， 被认为是下一代的平面显示器新兴应用技术。 LCD 都需要背光， 而 OLED 不需要， 因为它是自发光的。 这样同样的显示 OLED 效果要来得更好一些。 以目前的技术， OLED 的尺寸还难以大型化， 但是分辨率确可以做到很高。 我们使用的是 0.96 寸 OLED显示屏， 内部驱动芯片是 SSD1306， 如下图所示：

![屏幕截图 2024 08 15 091628](https://img.picgo.net/2024/08/15/-2024-08-15-091628e2e2f65194937c6b.png)

该屏有以下特点：

- 0.96 寸 OLED 有黄蓝， 白， 蓝三种颜色可选； 其中黄蓝是屏上 1/4 部分为黄光， 下 3/4 为蓝； 而且是固定区域显示固定颜色， 颜色和显示区域均不能修改； 白光则为纯白， 也就是黑底白字； 蓝色则为纯蓝， 也就是黑底蓝字。

- 分辨率为 128*64

- 多种接口方式； OLED 裸屏总共种接口包括： 6800、 8080 两种并行接口方式、 3 线或 4 线的串行 SPI 接口方式、 IIC 接口方式（只需要 2 根线就可以控制 OLED） ， 这五种接口是通过屏上的 BS0-BS2 来配置的。

本教程使用的是 0.96 寸 OLED（IIC 接口） 模块， 如下所示：

![屏幕截图 2024 08 15 092123](https://img.picgo.net/2024/08/15/-2024-08-15-092123ded8771b0d54e813.png)

脚功能介绍：

GND： 电源地； VDD： 电源正（3-5.5V） ； SCK： I2C 时钟管脚； SDA： I2C 数据管脚；

I2C 是用于设备之间通信的双线协议， 在物理层面， 它由 2 条线组成： SCL和 SDA， 分别是时钟线和数据线。 也就是说不同设备间通过这两根线就可以进行通信。

ESP32 有 2 硬件 I2C 接口和 N 个软件 I2C 接口， 硬件 I2C 总线默认的 IO 如下：

![屏幕截图 2024 08 15 092219](https://img.picgo.net/2024/08/15/-2024-08-15-092219ce06536c257ab93c.png)

硬件 I2C 接口通过配置可在任意 IO 口使用。 软件 I2C 接口可通过配置在任意 IO 口使用， 相当于使用 IO 口模拟 I2C 时序。 本实验使用软件 I2C 来与 OLED通信。

## 2. 硬件设计

本实验使用到硬件资源如下：

- 0.96存IIC接口OLED模块

- ESP32 GPIO

OLED接口电路如下：

![屏幕截图 2024 08 15 092356](https://img.picgo.net/2024/08/15/-2024-08-15-0923564721baa6800bfe0e.png)

从上图可知， 板载 4 路舵机接口均连接到指定 IO。

本章实验使用 ESP32 的 IO18、 23 引脚， 接线如下所示：

![屏幕截图 2024 08 15 092438](https://img.picgo.net/2024/08/15/-2024-08-15-092438f817675dd2d71154.png)

## 3. 软件设计

### 3.1 MicroPython函数使用

本实验需要使用到 MicroPython 的 machine 模块来定义 Pin 口和 I2C 初始化。 具体如下：

![屏幕截图 2024 08 15 093326](https://img.picgo.net/2024/08/15/-2024-08-15-09332638fb012b8472f1c6.png)

定义好 I2C 后， 还需要驱动一下 OLED。

MicroPython 固件库内并没有集成 SSD1306 驱动模块， 因此需要我们自己实现， 对于不了解 I2C 总线时序和 SSD1306 命令的用户来说， 要编写出驱动是困难的。 MicroPython 拥有着庞大的用户群， 自然 SSD1306 模块也有开源的代码， 直接拿过来使用即可。

![屏幕截图 2024 08 15 093419](https://img.picgo.net/2024/08/15/-2024-08-15-0934195eab17c3ceea3cfb.png)

### 3.2 代码分析

```python
#导入Pin模块
from machine import Pin
import time
from machine import SoftI2C
from ssd1306 import SSD1306_I2C  #I2C的oled选该方法

#创建硬件I2C对象
#i2c=I2C(0,sda=Pin(19), scl=Pin(18), freq=400000)

#创建软件I2C对象
i2c = SoftI2C(sda=Pin(23), scl=Pin(18))
#创建OLED对象，OLED分辨率、I2C接口
oled = SSD1306_I2C(128, 64, i2c) 

#程序入口
if __name__=="__main__":
    oled.fill(0)  #清空屏幕
    oled.show()  #执行显示
    
    oled.text("Hello World!",0,0,1)  #显示字符串
    oled.show()  #执行显示
    
    oled.pixel(10,20,1)  #显示一个像素点
    oled.hline(0,10,100,1)  #画横线
    oled.vline(120,0,30,1)  #画竖线
    oled.line(10,40,100,60,1)  #画指定坐标直线
    oled.rect(50,20,50,30,1)  #画矩形
    oled.fill_rect(60,30,30,20,1)  #画填充矩形
    oled.show()  #执行显示
    
    time.sleep(2)
    oled.fill(0)  #清空屏幕
    oled.text("Hello World!",0,0,1)
    oled.show()  #执行显示
    time.sleep(1)
    
    oled.scroll(10,0)  #指定像素X轴移动
    oled.fill_rect(0,0,10,8,0)  #清除移动前显示区
    oled.show()  #执行显示
    time.sleep(1)
    
    oled.scroll(0,10)  #指定像素Y轴移动
    oled.fill_rect(0,0,128,10,0)  #清除移动前显示区
    oled.show()  #执行显示
    while True:
        pass
        
```

---

2024.8.23 第一次修订，后期不再维护
