from machine import Pin, PWM
import time

led1 = PWM(Pin(15), freq=1000, duty=0) # 参数说明：Pin(15) 控制的引脚；freq=1000 频率；duty=0 初始占空比

# 主函数
if __name__ == '__main__':
    duty_value = 0 # 初始占空比
    fx = 1 # 1 正序，0 逆序
    while True:
        if fx == 1: # 正序
            duty_value += 10 # 增加 10 度
            if duty_value > 1010: # 最大值 1010
                fx = 0 # 切换方向
        else:
            duty_value -= 10 # 减少 10 度
            if duty_value < 10: # 最小值 10
                fx = 1 # 切换方向
        led1.duty(duty_value) # 设置占空比
        time.sleep_ms(10)       
