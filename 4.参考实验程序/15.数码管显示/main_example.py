from machine import Pin
import time
import tm1637

smg = tm1637.TM1637(clk=Pin(16), dio=Pin(17)) # 定义数码管控制对象

if __name__ == '__main__':
    # smg.number(1, 24) # 显示小数01.24
    # smg.hex(123) # 将十进制转换成16进制显示
    # smg.brightness(7) # 设置亮度为7
    # smg.temperature(25) # 显示温度符号，整数温度值
    # smg.show("1234") # 字符串显示，显示整数
    while True:
        smg.scroll("1314-520", 500) # 滚动显示字符串，每秒500ms滚动一次
    # n = 0
    # while True:
    #     smg.number(n) # 显示数字
    #     n += 1
    #     time.sleep(1) # 等待1秒
