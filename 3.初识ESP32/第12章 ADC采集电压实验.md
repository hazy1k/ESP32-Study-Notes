# 第十二章 ADC采集电压实验

## 1. 导入

ADC（analog to digital converter） 即模数转换器， 它可以将模拟信号转换为数字信号。 由于单片机只能识别二进制数字， 所以外界模拟信号常常会通过ADC 转换成其可以识别的数字信息。 常见的应用就是将变化的电压转成数字信号。

ADC 功能在 ESP32 引脚 32-39 上可用。 请注意， 使用默认配置时， ADC 引脚上的输入电压必须介于 0.0v 和 1.0v 之间（任何高于 1.0v 的值都将读为 4095） 。如果需要增加测量范围， 需要配置衰减器。

## 2. 硬件设计

本实验使用到硬件资源如下：

- 电位器

- ESP32 GPIO

ADC电位器电路如下：

![屏幕截图 2024 08 09 095746](https://img.picgo.net/2024/08/09/-2024-08-09-095746236118c6428c1ef1.png)

由图可知， J2 端子的 R_ADC 脚为电位器电压输出端， 可将该引脚与 ESP32的 ADC 脚连接即可采集。

本章实验使用 ESP32 的 IO34 引脚， 接线如下所示：

## 3. 软件设计

### 3.1 MicroPython函数使用

ADC 在 machine 的 ADC 模块中， 我们也是只需要了解其构造对象函数和使用方法即可。

![屏幕截图 2024 08 09 095929](https://img.picgo.net/2024/08/09/-2024-08-09-095929ac5be0f7f1afedc2.png)

使用方法如下：

![屏幕截图 2024 08 09 100013](https://img.picgo.net/2024/08/09/-2024-08-09-100013fafd2e0d50fd8aba.png)

### 3.2 代码分析

```python
from machine import Pin, ADC
from machine import Timer

adc = ADC(Pin(34)) # 定义ADC控制对象
adc.atten(ADC.ATTN_11DB) # 开启衰减，量程增大到3.3V

# 定时器0中断函数
def time0_irq(time0):
    adc_vol = 3.3 *adc.read() / 4095 # 计算电压值
    print("ADC电压值： %.2f V" % adc_vol)

if __name__ == '__main__':
    time0 = Timer(0) # 创建定时器0对象
    time0.init(period=1000, mode=Timer.PERIODIC, callback=time0_irq) # 初始化定时器0，周期1000ms，模式为周期性触发，回调函数为time0_irq
    while True:
        pass

```

---

2024.8.22 第一次修订，后期不再维护
