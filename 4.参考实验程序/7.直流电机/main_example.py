from machine import Pin
import time

# 定义直流电机控制对象
motor = Pin(15, Pin.OUT, Pin.PULL_DOWN) # 定义引脚15为输出模式，并下拉电阻

# 主函数
if __name__ == '__main__':
    motor.value(1) # 初始状态开启
    time.sleep(50) # 持续10秒
    motor.value(0) # 关闭电机
    while True:
        pass # 程序阻塞，等待用户输入
