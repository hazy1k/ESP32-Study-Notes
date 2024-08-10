from machine import Pin,RTC
import time

rtc = RTC() # 定义RTC控制对象

week = ("星期一","星期二","星期三","星期四","星期五","星期六","星期日")

if __name__ == '__main__':
    while True:
        date_time = rtc.datetime() # 获取当前时间
        print("日期：{}年{}月{}日 {} {}:{}:{}".format(date_time[0],date_time[1],date_time[2],week[date_time[3]],date_time[4],date_time[5],date_time[6]))
        time.sleep(1) # 延时1秒
        