from machine import Pin
import time

# a定义按键控制对象
key1 = Pin(14, Pin.IN, Pin.PULL_UP) # 使用引脚14，输入模式，上拉电阻
key2 = Pin(27, Pin.IN, Pin.PULL_UP)
key3 = Pin(26, Pin.IN, Pin.PULL_UP)
key4 = Pin(25, Pin.IN, Pin.PULL_UP)

# 定义led控制对象
led1 = Pin(15, Pin.OUT)
led2 = Pin(2, Pin.OUT)
led3 = Pin(0, Pin.OUT)
led4 = Pin(4, Pin.OUT)

# 定义led初始状态
led1_state,led2_state,led3_state,led4_state = 1,1,1,1

# key1外部中断函数
def key1_irq(key1):
    global led1_state # 声明全局变量
    time.sleep_ms(10) # 延时10ms，防止抖动
    if key1.value() == 0: # 按键按下
        led1_state = not led1_state # 翻转led状态
        led1.value(led1_state) # 控制led

# key2外部中断函数
def key2_irq(key2):
    global led2_state
    time.sleep_ms(10)
    if key2.value() == 0:
        led2_state = not led2_state
        led2.value(led2_state)

# key3外部中断函数
def key3_irq(key3):
    global led3_state
    time.sleep_ms(10)
    if key3.value() == 0:
        led3_state = not led3_state
        led3.value(led3_state)

# key4外部中断函数
def key4_irq(key4):
    global led4_state
    time.sleep_ms(10)
    if key4.value() == 0:
        led4_state = not led4_state
        led4.value(led4_state)

# 主函数
if __name__ == '__main__':
    led1.value(led1_state) # 初始状态
    led2.value(led2_state)
    led3.value(led3_state)
    led4.value(led4_state)

    key1_irq(key1_irq, Pin.IRQ_FALLING) # 配置key1外部中断，下降沿触发
    key2_irq(key2_irq, Pin.IRQ_FALLING)
    key3_irq(key3_irq, Pin.IRQ_FALLING)
    key4_irq(key4_irq, Pin.IRQ_FALLING)

    while True:
        pass # 程序阻塞，等待外部中断