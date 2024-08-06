from machine import Pin
from machine import Timer

led1 = Pin(15, Pin.OUT) # 定义LED1引脚
led1_state = 0 # 初始化led1           

# 定时器0中断函数
def time0_irq(time0):
    global led1_state
    led1_state = not led1_state # 翻转LED1状态
    led1.value(led1_state) # 设置LED1状态

# 主函数
if __name__ == "__main__" :
    led1.value(led1_state) # 熄灭LED1

    time0 = Timer(0) # 创建time0定时器对象
    time0.init(period=500, mode=Timer.PERIODIC, callback=time0_irq) # 参数说明：周期为500ms，模式为周期性，回调函数为time0_irq

    while True:
        pass
