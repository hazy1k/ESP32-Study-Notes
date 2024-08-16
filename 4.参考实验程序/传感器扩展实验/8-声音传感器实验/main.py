'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：声音传感器实验
接线说明：声音传感器模块-->ESP32 IO
         AO-->34
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，当传感器检测到声音，在Shell控制台上显示计数次数及声音大小值

注意事项：

'''

from machine import Pin,ADC
from time import sleep

sound = 34  

# 初始化GPIO口
def setup():
    global sound_ADC
    sound_ADC = ADC(Pin(sound))     
    sound_ADC.atten(ADC.ATTN_11DB)  # 11dB 衰减, 最大输入电压约3.6v

def ratio_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

# 循环函数
def loop():
    count = 0                                                 # 计数值
    while True:                                               # 无限循环
        voiceValue = round(ratio_map(sound_ADC.read(), 0, 4095, 0, 255)) # 读取ADC上的模拟值
        if voiceValue:                                # 当声音值不为0
            print ("Sound Value:", voiceValue)        # 打印出声音值
            if voiceValue > 25:              # 如果声音传感器读取值大于25
                print ("Voice detected! ", count)     # 打印出计数值
                count += 1                            # 计数值累加
            sleep(0.2)                                # 延时 200ms

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
