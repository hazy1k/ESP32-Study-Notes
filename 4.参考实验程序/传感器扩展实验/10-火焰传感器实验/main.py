'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：火焰传感器实验
接线说明：火焰传感器模块-->ESP32 IO
         AO-->34
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，在Shell控制台中输出传感器检测的火焰强度值

注意事项：

'''

from machine import Pin,ADC
from time import sleep

flame = 34   # ADC6复用管脚为GP34  

# 初始化GPIO口
def setup():
    global flame_ADC

    flame_ADC = ADC(Pin(flame))     # ADC 采集
    flame_ADC.atten(ADC.ATTN_11DB)  # 11dB 衰减, 最大输入电压约3.6v

# 循环函数
def loop():
    status = 1 # 状态值
    while True:                                 # 无限循环
        print (flame_ADC.read())                # 读取ADC6的值，打印出火焰传感器值
        sleep(0.2)                              # 延时200ms

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
