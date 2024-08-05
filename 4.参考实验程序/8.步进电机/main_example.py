from machine import Pin
import time

# 定义按键控制对象
key1 = Pin(14, Pin.IN, Pin.PULL_UP) # 使用引脚14作为输入，并上拉电阻
key2 = Pin(27, Pin.IN, Pin.PULL_UP)
key3 = Pin(26, Pin.IN, Pin.PULL_UP)
key4 = Pin(25, Pin.IN, Pin.PULL_UP)

# 定义步进电机控制对象
motor_a = Pin(15, Pin.OUT, Pin.PULL_DOWN) # 使用引脚15作为输出，并下拉电阻
motor_b = Pin(2, Pin.OUT, Pin.PULL_DOWN)
motor_c = Pin(0, Pin.OUT, Pin.PULL_DOWN)
motor_d = Pin(4, Pin.OUT, Pin.PULL_DOWN)

# 定义按键键值
KEY1_PRESS,KEY2_PRESS,KEY3_PRESS,KEY4_PRESS = 1,2,3,4
key_en = 1
# 按键扫描函数(前面已经讲过啦)
def key_scan():
    global key_en
    if key_en == 1 and (key1.value() == 0 or key2.value() == 0 or key3.value() == 0 or key4.value() == 0)
    time.sleep_ms(10)
    key_en = 0
    if key1.value() == 0:
        return KEY1_PRESS
    elif key2.value() == 0:
        return KEY2_PRESS
    elif key3.value() == 0:
        return KEY3_PRESS
    elif key4.value() == 0:
        return KEY4_PRESS
    elif key1.value() == 1 and key2.value() == 1 and key3.value() == 1 and key4.value() == 1:
        key_en = 1
    return 0    

# 步进电机发送脉冲函数
def step_motor_send_pulse(step, fx): # step:步进值，fx:步进方向
    temp = step # 保存当前步进值
    if fx == 0: # 如果步进方向为正
        temp = 7 - step # 反转步进值
    # 步进值设定    
    if temp == 0: 
        motor_a.value(1)
        motor_b.value(0)
        motor_c.value(0)
        motor_d.value(0)
    elif temp == 1:
        motor_a.value(1)
        motor_b.value(1)
        motor_c.value(0)
        motor_d.value(0)
    elif temp == 2:
        motor_a.value(0)
        motor_b.value(1)
        motor_c.value(0)
        motor_d.value(0)
    elif temp == 3:
        motor_a.value(0)
        motor_b.value(1)
        motor_c.value(1)
        motor_d.value(0)  
    elif temp == 4:
        motor_a.value(0)
        motor_b.value(0)
        motor_c.value(1)
        motor_d.value(0)
    elif temp == 5:
        motor_a.value(0)
        motor_b.value(0)
        motor_c.value(1)
        motor_d.value(1)    
    elif temp == 6:
        motor_a.value(0)
        motor_b.value(0)
        motor_c.value(0)
        motor_d.value(1)      
    elif temp == 7:
        motor_a.value(1)
        motor_b.value(0)
        motor_c.value(0)
        motor_d.value(1)      

# 主函数
if __name__ == '__main__':
    key = 0 # 按键值初始化
    fx1 = 1 # 步进方向初始化，默认正方向
    STEM_MAX = 1 # 步进最大值
    STEM_MIN = 5 # 步进最小值
    speed1 = STEM_MAX # 步进速度初始化
    step1 = 0 # 步进值初始化
    while True:
        key = key_scan() # 扫描按键
        if key == KEY1_PRESS:
            fx1 =not fx1 # 切换步进方向
        elif key == KEY2_PRESS:
            if speed1 > STEM_MAX: # 步进速度控制，加速，如果已经最大速度则减小
                speed1 -= 1
        elif key == KEY3_PRESS:
            if speed1 < STEM_MIN: # 步进速度控制，减速，如果已经最小速度则加大
                speed1 += 1
        step_motor_send_pulse(step1, fx1) # 步进电机发送脉冲
        step1 += 1 # 步进值加1
        if step1 == 8: # 步进值到达最大值则归零
            step1 = 0  # 步进值归零      
        time.sleep_ms(speed1) # 步进速度控制，延时
