'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：烟雾传感器检测实验
接线说明：MQ-2烟雾传感器模块-->ESP32 IO
         AO-->34
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，在Shell控制台中输出MQ2烟雾传感器检测的烟雾浓度值

注意事项：

'''

from machine import Pin,ADC
from time import sleep

gas = 34   # ADC复用管脚为GP34  

# 初始化GPIO口
def setup():
    global gas_ADC

    gas_ADC = ADC(Pin(gas))     # ADC 采集
    gas_ADC.atten(ADC.ATTN_11DB)  # 11dB 衰减, 最大输入电压约3.6v

# 循环函数
def loop():

    while True:                                 # 无限循环
        print (gas_ADC.read())                  # 读取ADC的值
        sleep(0.2)                              # 延时200ms

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
