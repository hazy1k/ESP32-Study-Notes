'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：LCD1602(IIC)液晶显示实验
接线说明：LCD1602(IIC)液晶模块-->ESP32 IO
         SCL-->25
         SDA-->26
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，LCD1602液晶显示字符信息，然后间隔一段时间滚动显示

注意事项：

'''

from machine import Pin,I2C
from time import sleep
from i2c_lcd import I2cLcd


# LCD 1602 I2C 地址
DEFAULT_I2C_ADDR = 0x27

# 初始化GPIO口
# def setup():
# global lcd
i2c = I2C(1,sda=Pin(26),scl=Pin(25),freq=400000)
lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)  # 初始化(设备地址, 背光设置)
lcd.putstr("Hello World!\nPRECHIN")       # 显示第一行信息及第二行信息
sleep(2)                                  # 延时2S

# 循环函数
def loop():
    space = '                '  # 空显信息
    greetings = 'PZ-ESP32 PRECHIN! ^_^' # 显示提示信息
    greetings = space + greetings # 显示信息拼接
    # 无线循环
    while True:
        tmp = greetings                    # 获取到显示信息
        for i in range(0, len(greetings)):          # 逐一显示
            lcd.putstr(tmp)                         # 逐个显示
            tmp = tmp[i:]
            sleep(0.8)                              # 延时800ms
            lcd.clear()                             # 清除显示

# 程序入口
if __name__ == '__main__':
#     setup()           # 初始化GPIO口
    loop()            # 循环函数
