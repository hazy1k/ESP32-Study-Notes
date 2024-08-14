#导入Pin模块
from machine import Pin
import time

#定义IRED控制对象
ired=Pin(14,Pin.IN,Pin.PULL_UP)

#存储红外遥控器键值
gired_data=[0,0,0,0]

#外部中断函数
def ired_irq(ired):
    ired_high_time=0  #保存高电平时间，鉴别数据1还是0
    
    if ired.value()==0:
        time_cnt=1000
        while (not ired.value()) and time_cnt:  #等待引导信号9ms低电平结束，若超过10ms强制退出
            time.sleep_us(10)
            time_cnt-=1
            if time_cnt==0:
                return
        
        if ired.value()==1:  #引导信号9ms低电平已过，进入4.5ms高电平
            time_cnt=500
            while ired.value() and time_cnt:  #等待引导信号4.5ms高电平结束，若超过5ms强制退出
                time.sleep_us(10)
                time_cnt-=1
                if time_cnt==0:
                    return
            for i in range(4):  #循环4次，读取4个字节数据
                for j in range(8):  #循环8次读取每位数据即一个字节
                    time_cnt=600
                    while (ired.value()==0) and time_cnt:  #等待数据1或0前面的0.56ms结束，若超过6ms强制退出
                        time.sleep_us(10)
                        time_cnt-=1
                        if time_cnt==0:
                            return
                    time_cnt=20
                    while ired.value()==1:  #等待数据1或0后面的高电平结束，若超过2ms强制退出
                        time.sleep_us(100)
                        ired_high_time+=1
                        if ired_high_time>20:
                            return
                    gired_data[i]>>=1  #先读取的为低位，然后是高位
                    if ired_high_time>=8:  #如果高电平时间大于0.8ms，数据则为1，否则为0
                        gired_data[i]|=0x80
                    ired_high_time=0  #重新清零，等待下一次计算时间
        if gired_data[2]!=~gired_data[3]:  #校验控制码与反码，错误则返回
            for i in range(4):
                gired_data[i]=0
                return
             
    print("红外遥控器操作码：0x%02X" % gired_data[2])
            
#程序入口
if __name__=="__main__":
    ired.irq(ired_irq,Pin.IRQ_FALLING)
    
    while True:
        pass
