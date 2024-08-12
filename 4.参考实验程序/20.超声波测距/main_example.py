from machine import Pin
import time
from hcsr04 import HCSR04

hcsr04 = HCSR04(trigger_pin = 4, echo_pin = 27) # 定义超声波传感器控制对象

if __name__ == '__main__':
    while True:
        distance = hcsr04.distance_cm() # 获取距离值
        print("距离是：%.2f CM" % distance)
        time.sleep(1) # 延时1秒
