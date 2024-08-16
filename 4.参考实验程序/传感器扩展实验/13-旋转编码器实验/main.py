'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：旋转编码器实验
接线说明：360度旋转编码器FOR模块-->ESP32 IO
         SW-->26
         DT-->25
         CLK-->32
         VCC-->5V
         GND-->GND
         
实验现象：程序下载成功后，旋转编码器，在Shell控制台输出计数值

注意事项：

'''

from machine import Pin,ADC
from time import sleep

RoAPin = 32    # 旋转编码器CLK管脚
RoBPin = 25    # 旋转编码器DT管脚
BtnPin = 26    # 旋转编码器SW管脚

globalCounter = 0  # 计数器值

flag = 0                # 是否发生旋转标志位
Last_RoB_Status = 0     # DT 状态
Current_RoB_Status = 0  # CLK 状态

# 初始化GPIO口
def setup():
    global clk_RoA
    global dt_RoB
    global sw_BtN

    clk_RoA =  Pin(RoAPin,Pin.IN) # 旋转编码器CLK管脚,设置为输入模式
    dt_RoB = Pin(RoBPin,Pin.IN)   # 旋转编码器DT管脚,设置为输入模式
    sw_BtN = Pin(BtnPin,Pin.IN, Pin.PULL_UP) # 设置BtnPin管脚为输入模式，上拉至高电平(3.3V)
    # 初始化中断函数，当SW管脚为0，使能中断
    sw_BtN.irq(trigger=Pin.IRQ_FALLING,handler=btnISR)

# 旋转编码方向位判断函数
def rotaryDeal():
    global flag                   # 是否发生旋转标志位
    global Last_RoB_Status
    global Current_RoB_Status
    global globalCounter         # 计数器值

    Last_RoB_Status = dt_RoB.value()

    while(not clk_RoA.value()):       # 判断CLK管脚的电平变化来区分方向
        Last_RoB_Status = dt_RoB.value()
        flag = 1    # 发生旋转标记
    if flag == 1:   # 标记位为1 发生了旋转
        flag = 0    # 复位标记位
        if (Last_RoB_Status == 0) and (Current_RoB_Status == 1):
            globalCounter = globalCounter + 1   # 逆时针方向，正
        if (Last_RoB_Status == 1) and (Current_RoB_Status == 0):
            globalCounter = globalCounter - 1   # 顺时针方向，负

# 中断函数，当SW管脚为0，使能中断
def btnISR(chn):
    global globalCounter
    globalCounter = 0 # 给计数器赋0
    #print ('globalCounter = %d' % globalCounter)

# 循环函数
def loop():
    global globalCounter
    tmp = 0   # 当前状态判断
    while True:
        rotaryDeal()      # 旋转编码方向位判断函数
        if tmp != globalCounter: # 判断状态值发生改变
            print ('globalCounter = %d' % globalCounter) # 打印出状态信息
            tmp = globalCounter    #  把当前状态赋值到下一个状态，避免重复打印

# 程序入口
if __name__ == '__main__':
    setup()           # 初始化GPIO口
    loop()            # 循环函数
