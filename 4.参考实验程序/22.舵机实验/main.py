#导入Pin模块
from machine import Pin
import time
from servo import Servo

#定义SG90舵机控制对象
my_servo = Servo(Pin(17))

#程序入口
if __name__=="__main__":

    while True:
        my_servo.write_angle(0)  #角度0°
        time.sleep(0.5)
        my_servo.write_angle(45)  #角度45°
        time.sleep(0.5)
        my_servo.write_angle(90)  #角度90°
        time.sleep(0.5)
        my_servo.write_angle(135)  #角度135°
        time.sleep(0.5)
        my_servo.write_angle(180)  #角度180°
        time.sleep(0.5)
