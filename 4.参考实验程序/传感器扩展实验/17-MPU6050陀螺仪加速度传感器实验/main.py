'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：MPU6050陀螺仪加速度传感器实验
接线说明：MPU6050陀螺仪加速度传感器模块-->ESP32 IO
         SCL-->25
         SDA-->26
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，转动传感器，在Shell控制台输出XY轴角度值

注意事项：

'''

from machine import Pin
import utime
import math
import mpu6050


# 初始化GPIO口
def setup():
    mpu = mpu6050.MPU6050()
    mpu.setSampleRate(200) # 设置采样率
    mpu.setGResolution(2)  # 设置g分辨率                            

# 均值处理
def averageMPU( count, timing_ms):
    gx = 0
    gy = 0
    gz = 0
    gxoffset =  0.07
    gyoffset = -0.04
    for i in range(count):
        g=mpu.readData()
        # offset mpu
        gx = gx + g.Gx - gxoffset
        gy = gy + g.Gy - gyoffset
        gz = gz + g.Gz
        utime.sleep_ms(timing_ms)
    return gx/count, gy/count, gz/count

# 循环函数
def loop():
    while True:
        gx, gy, gz = averageMPU(20,5)
        # calculate vector dimension
        vdim = math.sqrt( gx*gx + gy*gy + gz*gz)

        # get x angle
        rad2degree= 180 / math.pi
        angleX =  rad2degree * math.asin(gx / vdim)
        angleY =  rad2degree * math.asin(gy / vdim)
        # 获取X，Y的倾斜角度
        print('angleY = {0:0.2f} °'.format(-angleY))
        print('         angleX = {0:0.2f} °'.format(-angleX))   

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
