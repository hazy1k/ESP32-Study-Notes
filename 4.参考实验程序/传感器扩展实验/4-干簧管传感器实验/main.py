'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：干簧管传感器实验
接线说明：干簧管传感器模块-->ESP32 IO
         DO-->26
         VCC-->5V
         GND-->GND
         
         LED模块-->ESP32 IO
         D1-->15
         
实验现象：程序下载成功后，若传感器感应到有一定磁力的时候，D1指示灯亮，否则不亮
注意事项：

'''

from machine import Pin
from time import sleep

TiltPin  = 26     # 传感器Pin端口
ledpin   = 15    # LED端口
n = 0

# 初始化GPIO口
def setup():
    global Tilt
    global led

    led = Pin(ledpin,Pin.OUT) # 设置LED管脚为输出模式
    Tilt = Pin(TiltPin, Pin.IN, Pin.PULL_UP) # 设置为输入模式
    # 中断函数，调用call_back函数
    Tilt.irq(trigger=Pin.IRQ_FALLING,handler=call_back)

# 中断函数，模块切斜，响应中断函数
def call_back(Tilt):
    global n
    n=not n
    led.value(n)

# 循环函数
def loop():
    while True:
        pass

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
