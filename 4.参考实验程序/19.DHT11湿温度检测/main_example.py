#导入Pin模块
from machine import Pin
import time
import dht

#定义DHT11控制对象
dht11=dht.DHT11(Pin(27))

#程序入口
if __name__=="__main__":
    time.sleep(1)  #首次启动间隔1S让传感器稳定
    while True:
        dht11.measure()  #调用DHT类库中测量数据的函数
        temp = dht11.temperature()
        humi = dht11.humidity()
        if temp==None:
            print("DHT11传感器检测失败！")
        else:
            print("temp=%d °C  humi=%d %%" %(temp,humi))
        time.sleep(2)  #如果延时时间过短，DHT11温湿度传感器不工作
