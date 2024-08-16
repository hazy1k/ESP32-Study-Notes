'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：PIR人体热释电感应模块实验
接线说明：PIR人体热释电感应模块-->ESP32 IO
         OUT-->26
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，将传感器检测是否有人，在Shell控制台输出对应的信息

注意事项：传感器检测有人，则输出高电平，反之输出低电平

'''

from machine import Pin
from utime import sleep

pirPin = 27    # PIR人体热释电管脚PIN

# 初始化GPIO口
def setup():
    global pir
    
    pir = Pin(pirPin,Pin.IN,Pin.PULL_DOWN)                            

# 循环函数
def loop():
    while True:
        if pir.value() == 1:  # 检测到有人
            print ('Detect someone...')
        else:
            print ('unmanned!!!') 

        sleep(0.2) # 延时200ms  

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
