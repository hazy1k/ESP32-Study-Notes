from machine import Pin
import time

# 定义按键控制对象
key1 = Pin(14, Pin.IN, Pin.PULL_UP) # 参数：引脚号，模式，上拉电阻
key2 = Pin(27, Pin.IN, Pin.PULL_UP)
key3 = Pin(26, Pin.IN, Pin.PULL_UP)
key4 = Pin(25, Pin.IN, Pin.PULL_UP)

# 定义LED对象
led1 = Pin(15, Pin.OUT) # 参数：引脚号，模式
led2 = Pin(2, Pin.OUT)
led3 = Pin(0, Pin.OUT)
led4 = Pin(4, Pin.OUT)

# 定义按键键值
KEY1_PRESS,KEY2_PRESS,KEY3_PRESS,KEY4_PRESS = 1,2,3,4
key_en = 1

# 按键扫描函数
def key_scan():
    global key_en # 声明全局变量
    if key_en == 1 and (key1.value() == 0 or key2.value() == 0 or key3.value() == 0 or key4.value() == 0): # 按键被按下
        time.sleep_ms(10) # 延时10ms,消抖
        key_en = 0 # 按键被按下,禁止重复按键
        if key1.value() == 0:
            return KEY1_PRESS
        elif key2.value() == 0:
            return KEY2_PRESS
        elif key3.value() == 0:
            return KEY3_PRESS
        elif key4.value() == 0:
            return KEY4_PRESS
    elif key1.value() == 1 and key2.value() == 1 and key3.value() == 1 and key4.value() == 1: # 按键被释放
        key_en = 1 # 按键被释放,允许按键
    return 0 # 按键未被按下

# 主函数
if __name__ == '__main__':
    key = 0
    i_led1,i_led2,i_led3,i_led4 = 0,0,0,0 # 定义LED初始状态
    led1.value(i_led1)
    led2.value(i_led2)
    led3.value(i_led3)
    led4.value(i_led4)
    while True:
        key = key_scan() # 扫描按键
        if key == KEY1_PRESS: # 按键1被按下
            i_led1 = 1 - i_led1 # 切换LED状态
            led1.value(i_led1)
        elif key == KEY2_PRESS: # 按键2被按下
            i_led2 = 1 - i_led2
            led2.value(i_led2)
        elif key == KEY3_PRESS: # 按键3被按下
            i_led3 = 1 - i_led3
            led3.value(i_led3)
        elif key == KEY4_PRESS: # 按键4被按下
            i_led4 = 1 - i_led4
            led4.value(i_led4)
            