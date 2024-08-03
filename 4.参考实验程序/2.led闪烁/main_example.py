# led闪烁实验
from machine import Pin # 导入Pin模块
import time # 导入time模块

led1 = Pin(15, Pin.OUT) # 定义led1引脚为输出模式

while True:
    led1.value(1) # 点亮led
    time.sleep(0.5) # 持续0.5秒
    led1.value(0) # 熄灭led
    time.sleep(0.5) # 持续0.5秒
    