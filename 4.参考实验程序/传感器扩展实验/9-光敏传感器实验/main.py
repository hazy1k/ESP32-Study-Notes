'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：光敏传感器实验
接线说明：光敏传感器模块-->ESP32 IO
         AO-->34
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，在Shell控制台中输出传感器检测的光线值

注意事项：

'''

from machine import Pin,ADC
from time import sleep

light = 34  

# 初始化GPIO口
def setup():
    global light_ADC
    light_ADC = ADC(Pin(light))     
    light_ADC.atten(ADC.ATTN_11DB)  # 11dB 衰减, 最大输入电压约3.6v

# 循环函数
def loop():
    status = 1 # 状态值
    while True:                                               # 无限循环
        print ('Light Value: ', light_ADC.read()) # 读取ADC6的值16-bits，获取光敏模拟量值
        sleep(0.2)                                            # 延时200ms

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
