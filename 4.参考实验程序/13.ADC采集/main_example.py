from machine import Pin, ADC
from machine import Timer

adc = ADC(Pin(34)) # 定义ADC控制对象
adc.atten(ADC.ATTN_11DB) # 开启衰减，量程增大到3.3V

# 定时器0中断函数
def time0_irq(time0):
    adc_vol = 3.3 *adc.read() / 4095 # 计算电压值
    print("ADC电压值： %.2f V" % adc_vol)

if __name__ == '__main__':
    time0 = Timer(0) # 创建定时器0对象
    time0.init(period=1000, mode=Timer.PERIODIC, callback=time0_irq) # 初始化定时器0，周期1000ms，模式为周期性触发，回调函数为time0_irq
    while True:
        pass
