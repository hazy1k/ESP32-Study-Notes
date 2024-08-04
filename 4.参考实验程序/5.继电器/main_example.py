# 导入Pin模块
from machine import Pin
import time

# 定义LED引脚
relay = Pin(25, Pin.OUT)
    
if __name__ == '__main__':
    i = 0
    while True:
        i =not i # 翻转LED状态
        relay.value(i) # 设置LED状态
        time.sleep(1) # 延时1秒
# 继电器模块每隔一秒钟翻转一次LED的状态，实现开关功能。
        