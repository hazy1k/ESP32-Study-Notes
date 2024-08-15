'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：WIFI实验-连接无线路由器
接线说明：LED模块-->ESP32 IO
         (D1)-->(15)
         
实验现象：程序下载成功后，软件shell控制台输出当前IP、子网掩码、网关的地址信息
         
注意事项：ESP32 WIFI作为客户端连接路由器热点，然后电脑也连接路由器，此时可连接成功输出信息

'''

#导入Pin模块
from machine import Pin
import time
import network

#定义LED控制对象
led1=Pin(15,Pin.OUT)

#路由器WIFI账号和密码
ssid="puzhong88"
password="PUZHONG88"

#WIFI连接
def wifi_connect():
    wlan=network.WLAN(network.STA_IF)  #STA模式
    wlan.active(True)  #激活
    start_time=time.time()  #记录时间做超时判断
    
    if not wlan.isconnected():
        print("conneting to network...")
        wlan.connect(ssid,password)  #输入 WIFI 账号密码
        
        while not wlan.isconnected():
            led1.value(1)
            time.sleep_ms(300)
            led1.value(0)
            time.sleep_ms(300)
            
            #超时判断,15 秒没连接成功判定为超时
            if time.time()-start_time>15:
                print("WIFI Connect Timeout!")
                break
    
    else:
        led1.value(0)
        print("network information:", wlan.ifconfig())
            

#程序入口
if __name__=="__main__":
    
    wifi_connect()
