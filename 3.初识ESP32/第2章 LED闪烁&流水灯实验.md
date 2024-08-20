# 第二章 LED闪烁&流水灯实验

## 1. 硬件设计

参考上一章

## 2. 软件设计

- led闪烁

```python
# led闪烁实验
from machine import Pin # 导入Pin模块
import time # 导入time模块

led1 = Pin(15, Pin.OUT) # 定义led1引脚为输出模式

while True:
    led1.value(1) # 点亮led
    time.sleep(0.5) # 持续0.5秒
    led1.value(0) # 熄灭led
    time.sleep(0.5) # 持续0.5秒
```

![屏幕截图 2024 08 03 161024](https://img.picgo.net/2024/08/03/-2024-08-03-1610241092e223913bb765.png)

- 流水灯

```python
# 流水灯实验
from machine import Pin # 导入Pin模块
import time # 导入time模块

led_pin = [15, 2, 0, 4, 16, 17, 5, 18] # 定义LED控制引脚
leds = [] # 定义LED列表，保存LED对象
for i in range(8):
    leds.append(Pin(led_pin[i], Pin.OUT)) # 循环创建LED对象并添加到列表中

# 程序入口
if __name__ == '__main__':
    # LED初始全部关闭
    for n in range(8):
        leds[n].value(0)

    # 循环显示LED
    while True:
        for n in range(8):
            leds[n].value(1)
            time.sleep(0.5)
        for n in range(8):
            leds[n].value(0)
            time.sleep(0.5)    
```

led闪烁倒是很简单，这个流水灯我们还是要详细解释一下：

- 我们利用了range()函数，range()函数是 Python 内置函数， 创建一个整数列表， 一般用于 for 循环当中，借助for循环和append，把控制引脚写入到led列表中

- 还有一个和c/c++完全不同的地方：

```python
if __name__=="__main__":
```

这句话是什么意思呢？ 只要你创建了一个模块（一个.py 文件） ， 这个模块就有一个内置属性 name 生成， 该模块的 name 的值取决于如何应用这个模块。简单来说就是， 如果你直接运行该模块， 那么______name______ == "______main______"；

如果你 import 一个模块， 那么模块 name 的值通常为模块文件名。

如果模块是被直接运行的， 则代码块被运行， 如果模块被 import， 则代码块不被运行。

通常我们习惯把这个作为程序入口函数， 就像 C、 C++、 JAVA 等语言一样，从 main 函数开始执行。

## 3. 小结

前面关于控制led的都算比较简单的了，属于新手关，没什么可好解释的，重点是熟悉Pin和time模块即可

后面就是蜂鸣器、按键、电机那些、再说串口、数码管、时钟、ADC，最后就是各种传感器了，关于WiFi之类的实验最后再来操作，等我们熟悉ESP32再来

---

2024.8.20 第一次修订，后期不再维护
