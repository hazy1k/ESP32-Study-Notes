'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：红外寻迹模块实验
接线说明：红外寻迹模块模块-->ESP32 IO
         DO-->26
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，传感器检测信息在Shell控制台输出

注意事项：传感器检测到白线时DO输出低电平，反之检测到黑线输出高电平

'''

from machine import Pin
import utime

TrackPin = 26 # 循迹传感器PIN管脚

# 初始化GPIO口
def setup():
    global Track
    # 设置TrackPin管脚为输入模式，上拉至高电平(3.3V)
    Track = Pin(TrackPin,Pin.IN,Pin.PULL_UP)                            

# 循环函数
def loop():
    while True:
        if Track.value() == 0:  # 检测到白色线
            print ('White line is detected')
        else:
            print ('...Black line is detected') # 检测到黑色线

        utime.sleep(0.2) # 延时200ms  

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
