from machine import Pin, UART # 导入Pin和UART模块
import time

# 定义UART控制对象
uart = UART(2,115200,rx=16,tx=17) # 参数: UART号,波特率,TX引脚,RX引脚

if __name__ == '__main__':
    uart.write('Hello, world!\r\n') # 发送数据
    while True:
        if uart.any(): # 如果接收到数据
            data = uart.read(128) # 读取数据
            uart.write(data) # 发送数据
