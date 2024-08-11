from machine import Pin
import time
import DS1302

# 定义DS1302的控制对象
ds1302 = DS1302.DS1302(clk=Pin(18), dio=Pin(19), cs=Pin(23))

week = ("星期一","星期二","星期三","星期四","星期五","星期六","星期日")

if __name__ == '__main__':
    while True:
        # 获取当前时间
        now = time.localtime()
        # 显示时间
        print("日期：{}年{}月{}日 {} {}:{}:{}".format(now[0], now[1], now[2], week[now[6]], now[3], now[4], now[5]))
        # 延时1秒
        time.sleep(1)
