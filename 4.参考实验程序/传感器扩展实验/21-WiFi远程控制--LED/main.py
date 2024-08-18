'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：WiFi远程控制LED
接线说明：LED模块-->ESP32 IO
         (D1)-->(15)
         
实验现象：程序下载成功后，软件shell控制台输出当前IP、子网掩码、网关的地址信息，在网络调试助手上
         连接成功后，可控制板载LED。
         
注意事项：ESP32 WIFI作为客户端连接路由器热点，然后电脑也连接路由器，此时可在电脑端使用网络调试助手，
         设置：协议类型：UDP，本机主机地址：电脑端IP地址，本机主机端口：8080

'''

#导入Pin模块
from machine import Pin
import time
import network
import socket



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
            #超时判断,15 秒没连接成功判定为超时
            if time.time()-start_time>15:
                print("WIFI Connect Timeout!")
                break
        return False
    
    else:
        print("network information:", wlan.ifconfig())
        return True

#启动网络
def start_udp():
    #创建udp套接字
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #绑定本地信息
    udp_socket.bind(("0.0.0.0", 7788))
    return udp_socket

#程序入口
if __name__=="__main__":
    #连接WIFI
    if wifi_connect():
        #创建UDP
        udp_socket = start_udp()
        #定义LED控制对象
        led1=Pin(15,Pin.OUT)
        #接收网络数据
        while True:
            recv_data, sender_info = udp_socket.recvfrom(1024)
            print("{}发送{}".format(sender_info, recv_data))
            recv_data_str = recv_data.decode("utf-8")
            try:
                print(recv_data_str)
            except Exception as ret:
                print("error:", ret)
            
            #处理接收的数据
            if recv_data_str == "led on":
                print("这里是要灯亮的代码...")
                led1.value(1)
            elif recv_data_str == "led off":
                print("这里是要灯灭的代码...")
                led1.value(0)
            
