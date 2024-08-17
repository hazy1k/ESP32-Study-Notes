#导入Pin模块
from machine import Pin
import time
from machine import Timer
import network
from simple import MQTTClient

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
        wlan.connect(ssid,password)  #输入WIFI账号和密码
        
        while not wlan.isconnected():
            led1.value(1)
            time.sleep_ms(300)
            led1.value(0)
            time.sleep_ms(300)
            
            #超时判断,15 秒没连接成功判定为超时
            if time.time()-start_time>150:
                print("WIFI Connect Timeout!")
                break
        return False
    
    else:
        led1.value(0)
        print("network information:", wlan.ifconfig())
        return True

#发布数据任务
def mqtt_send(tim):
    client.publish(TOPIC, "Hello PRECHIN")

#程序入口
if __name__=="__main__":
    
    if wifi_connect():
        SERVER="mq.tongxinmao.com"
        PORT=18830
        CLIENT_ID="PZ-ESP32"  #客户端ID
        TOPIC="/public/pz_esp32/1"  #TOPIC名称
        client = MQTTClient(CLIENT_ID, SERVER, PORT)
        client.connect()
        
        #开启RTOS定时器,周期 1000ms，执行MQTT通信接收任务
        tim = Timer(0)
        tim.init(period=1000, mode=Timer.PERIODIC,callback=mqtt_send)
        
