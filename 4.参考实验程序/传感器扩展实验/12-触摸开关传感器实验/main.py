'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：触摸开关传感器实验
接线说明：TTP223触摸开关传感器模块-->ESP32 IO
         SIG-->26
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，触摸传感器后，Shell控制台输出触摸信息

注意事项：

'''

from machine import Pin,ADC
from time import sleep

TouchPin = 26   # 触摸传感器管脚PIN  

# 初始化GPIO口
def setup():
    global touch_DO

    touch_DO = Pin(TouchPin, Pin.IN, Pin.PULL_DOWN)    # 设置TouchPin管脚为输入模式

# 循环函数
def loop():
    status=0
    while True:                                 # 无限循环
       status=touch_DO.value()  #读取触摸传感器值
       if status==1:
           print('触摸按下...')

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
