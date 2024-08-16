'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：红外避障传感器实验
接线说明：红外避障传感器模块-->ESP32 IO
         OUT-->26
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，当传感器检测到有障碍物时，在Shell控制台输出信息

注意事项：红外避障传感器检测有障碍物时，OUT输出低电平，否则输出高电平。

'''

from machine import Pin
from time import sleep

ObstaclePin = 26       # 红外避障传感器管脚PIN

# 初始化GPIO口
def setup():
    global ir_Obstacle
    # 设置ObstaclePin管脚为输入模式，上拉至高电平(3.3V)
    ir_Obstacle = Pin(ObstaclePin,Pin.IN,Pin.PULL_UP)

# 循环函数
def loop():
    while True:
        if (0 == ir_Obstacle.value()):      # 检测到障碍物
            print ("Detected Barrier!")     # 打印出障碍物信息
            sleep(0.2)                      # 延时200ms

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
