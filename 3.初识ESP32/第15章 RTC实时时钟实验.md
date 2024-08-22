# 第十五章 RTC实时时钟实验

## 1. 导入

时钟可以说是我们日常生活中最常用的东西了， 手表、 电脑、 手机等无时无刻不显示当前的时间。 可以说每一个电子爱好者心中都希望拥有属于自己制作的一个电子时钟， 接下来我们就用开发板来制作一个属于自己的电子时钟。

## 2. 硬件设计

由于 RTC 模块为 MicroPython 固件所含有的功能， 且在 Shell 控制台输出，因此只需 ESP32 开发板即可实现。

## 3. 软件设计

### 3.1 MicroPython函数使用

毫无疑问， 强大的 MicroPython 已经集成了内置时钟函数模块。 位于machine 的 RTC 模块中， 具体介绍如下：

![屏幕截图 2024 08 10 100207](https://img.picgo.net/2024/08/10/-2024-08-10-10020700d3681623e4b394.png)

使用方法如下：

![屏幕截图 2024 08 10 100414](https://img.picgo.net/2024/08/10/-2024-08-10-1004146b15849b5a712e79.png)

### 3.2 代码分析

```python
from machine import Pin,RTC
import time

rtc = RTC() # 定义RTC控制对象

week = ("星期一","星期二","星期三","星期四","星期五","星期六","星期日")

if __name__ == '__main__':
    while True:
        date_time = rtc.datetime() # 获取当前时间
        print("日期：{}年{}月{}日 {} {}:{}:{}".format(date_time[0],date_time[1],date_time[2],week[date_time[3]],date_time[4],date_time[5],date_time[6]))
        time.sleep(1) # 延时1秒
        
```

---

2024.8.22 第一次修订，后期不咋维护
