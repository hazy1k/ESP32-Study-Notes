'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：PS2操纵杆实验
接线说明：PS2操纵杆模块-->ESP32 IO
         VRX-->34
         VRY-->35
         SW-->36
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，操作PS2操纵杆时，在Shell控制台输出对应方向信息

注意事项：

'''

from machine import Pin,ADC
from time import sleep

VRX_ADC = 34 # ADC6复用管脚为GP34
VRY_ADC = 35 # ADC7复用管脚为GP35
SW_ADC =  36 # ADC0复用管脚为GP36

# 初始化GPIO口
def setup():
    global adcx
    global adcy
    global adcsw

    adcx = ADC(Pin(VRX_ADC))
    adcx.atten(ADC.ATTN_11DB)

    adcy = ADC(Pin(VRY_ADC))
    adcy.atten(ADC.ATTN_11DB)

    adcsw = ADC(Pin(SW_ADC))
    adcsw.atten(ADC.ATTN_11DB)


def ratio_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

# 方向判断函数
def direction():
    state = ['home', 'up', 'down', 'left', 'right', 'pressed']  # 方向状态信息
    i = 0

    adc_X = round(ratio_map(adcx.read(), 0, 4095, 0, 255))
    adc_Y = round(ratio_map(adcy.read(), 0, 4095, 0, 255))
    adc_SW = round(ratio_map(adcsw.read(), 0, 4095, 0, 255))
    #print("adc_x=%d,adc_y=%d,adc_sw=%d"%(adc_X,adc_Y,adc_SW))
    sleep(0.1)
    if  adc_X <= 30:
        i = 1 # up方向
    elif adc_X >= 255:
        i = 2 # down方向
    elif adc_Y >= 255:
        i = 3 # left方向
    elif adc_Y <= 30:
        i = 4 # right方向
    elif adc_SW == 0:#and adc_Y ==128:
        i = 5 # Button按下
    # home位置
    elif adc_X - 125 < 15 and adc_X - 125 > -15 and adc_Y -125 < 15 and adc_Y -125 > -15 and adc_SW == 255:
        i = 0

    return state[i]   # 返回状态

# 循环函数
def loop():
    status = ''    # 状态值赋空值
    while True:
        tmp = direction()   # 调用方向判断函数
        if tmp != None and tmp != status:  # 判断状态是否发生改变
            print (status) # 打印出方向位
            status = tmp # 把当前状态赋给状态值，以防止同一状态多次打印

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
