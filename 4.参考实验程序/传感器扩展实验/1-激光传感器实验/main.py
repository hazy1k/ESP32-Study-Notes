'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：激光传感器实验
接线说明：5V激光传感器模块-->ESP32 IO
         SIG-->15
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，激光间隔0.5秒点亮
注意事项：请勿直接用眼睛看激光光束！请勿直接用眼睛看激光光束！请勿直接用眼睛看激光光束！

'''

#导入Pin模块
from machine import Pin
from time import sleep

LaserPin = 15    # 定义激光传感器管脚为Pin15

# 初始化工作
def setup():
    global Laser
    Laser = Pin(LaserPin,Pin.OUT) # 设置Pin模式为输出模式
    Laser.value(0) # 设置激光传感器管脚为低电平(0V)关闭激光传感器

# 循环函数
def loop():
    while True:
        # 打开激光传感器
        Laser.value(1)
        sleep(0.5)  # 延时500ms

        # 关闭激光传感器
        Laser.value(0)
        sleep(0.5) # 延时500ms

# 程序入口
if __name__ == '__main__':
    setup()       #  初始化
    loop()        #  调用循环函数


