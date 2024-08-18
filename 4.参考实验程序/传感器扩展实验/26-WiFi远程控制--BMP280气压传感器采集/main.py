'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：WIFI远程控制--BMP280气压传感器采集
接线说明：LED模块-->ESP32 IO
         (D1)-->(15)
         
         BMP280气压传感器模块-->ESP32 IO
         SCL-->25
         SDA-->26
         VCC-->3V3
         GND-->GND
         
实验现象：程序下载成功后，手机连接的WIFI需和ESP32连接的WIFI处于同一频段（比如192.168.1.xx），
         然后在手机网页输入Shell控制台输出的本机IP地址即可进入手机端网页显示采集的传感器数据，
         可手动刷新页面更新数据显示。
         
注意事项：ESP32作为服务器，手机或电脑作为客户端

'''

#导入Pin模块
from machine import Pin
import time
import network
import socket
from bmp280 import BMP280

#定义LED控制对象
led1=Pin(15,Pin.OUT,Pin.PULL_DOWN)
#定义BMP280传感器对象
bus = I2C(1,sda= Pin(26), scl= Pin(25), freq=400000)


#连接的WIFI账号和密码
ssid = "PRECHIN"
password = "12345678"
        
#WIFI连接
def wifi_connect():
    wlan=network.WLAN(network.STA_IF)  #STA模式
    wlan.active(True)  #激活
    
    if not wlan.isconnected():
        print("conneting to network...")
        wlan.connect(ssid,password)  #输入 WIFI 账号密码
        
        while not wlan.isconnected():
            led1.value(1)
            time.sleep_ms(300)
            led1.value(0)
            time.sleep_ms(300)
        led1.value(0)
        return False
    else:
        led1.value(0)
        print("network information:", wlan.ifconfig())
        return True

#网页数据
def web_page():
    bme = BMP280(bus)
    humidity = 40
    html = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:,"><style>body { text-align: center; font-family: "Trebuchet MS", Arial;}
    table { border-collapse: collapse; width:35%; margin-left:auto; margin-right:auto; }
    th { padding: 12px; background-color: #0043af; color: white; }
    tr { border: 1px solid #ddd; padding: 12px; }
    tr:hover { background-color: #bcbcbc; }
    td { border: none; padding: 12px; }
    .sensor { color:white; font-weight: bold; background-color: #bcbcbc; padding: 1px;
    </style></head><body><h1>ESP32 BMP280 Acquisition</h1>
    <table><tr><th>MEASUREMENT</th><th>VALUE</th></tr>
    <tr><td>Temp. Celsius</td><td><span class="sensor">""" + str(bme.temperature) + """</span></td></tr>
    <tr><td>Pressure</td><td><span class="sensor">""" + str(bme.pressure) + """</span></td></tr>
    </body></html>"""
    return html

#程序入口
if __name__=="__main__":
    
    if wifi_connect():
        #SOCK_STREAM表示的是TCP协议，SOCK_DGRAM表示的是UDP协议
        my_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #创建socket连接
        # 将socket对象绑定ip地址和端口号
        my_socket.bind(('', 80))
        # 相当于电话的开机 括号里的参数表示可以同时接收5个请求
        my_socket.listen(5)
        
        while True:
            try:
                # 进入监听状态，等待别人链接过来，有两个返回值，
                #一个是对方的socket对象，一个是对方的ip以及端口
                client, addr = my_socket.accept()
                print('Got a connection from %s' % str(addr))
                # recv表示接收，括号里是最大接收字节
                request = client.recv(1024)
                request = str(request)
                print('Content = %s' % request)
                response = web_page()
                client.send('HTTP/1.1 200 OK\n')
                client.send('Content-Type: text/html\n')
                client.send('Connection: close\n\n')
                client.sendall(response)
                client.close()
            except OSError as e:
                conn.close()
                print('Connection closed')


