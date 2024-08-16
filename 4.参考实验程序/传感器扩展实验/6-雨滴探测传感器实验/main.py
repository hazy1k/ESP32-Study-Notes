'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：雨滴探测传感器实验
接线说明：雨滴探测传感器模块-->ESP32 IO
         DO-->26
         VCC-->5V
         GND-->GND
         AO-->34
         
         LED模块-->ESP32 IO
         D1-->15
         
实验现象：程序下载成功后，若传感器感应到有雨滴时，D1指示灯亮，否则不亮，同时通过Shell控制台输出雨量大小

注意事项：感应板上没有水滴时，DO输出为高电平，滴上一滴水，DO输出为低电平，AO模拟输出，
         可以连接单片机的AD口检测滴在上面的雨量大小。

'''

from machine import Pin,ADC
from time import sleep

TiltPin  = 26    # 传感器DO端口
ledpin   = 15    # LED端口
adcpin   = 34    # 传感器AO端口端口
n = 0

# 初始化GPIO口
def setup():
    global raind_ADC
    global raind_DO

    led = Pin(ledpin,Pin.OUT) # 设置LED管脚为输出模式
    raind_ADC = ADC(Pin(adcpin))        # ADC6复用管脚为GP34
    raind_ADC.atten(ADC.ATTN_11DB)      # 11dB 衰减, 最大输入电压约3.6v
    Tilt = Pin(TiltPin, Pin.IN, Pin.PULL_UP) # 设置为输入模式
    # 中断函数，调用call_back函数
    Tilt.irq(trigger=Pin.IRQ_FALLING,handler=call_back)

# 中断函数，模块切斜，响应中断函数
def call_back(Tilt):
    global n
    n=not n
    led.value(n)

# 循环函数
def loop():
    while True:
        print (raind_ADC.read())  # 输出模拟信号值
        sleep(1)
        

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
