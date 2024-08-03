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
