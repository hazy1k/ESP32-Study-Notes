'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：WIFI远程控制--继电器
接线说明：LED模块-->ESP32 IO
         (D1)-->(15)
         
         继电器模块-->ESP32 IO
         (REL)-->(25)
         
实验现象：程序下载成功后，手机连接的WIFI需和ESP32连接的WIFI处于同一频段（比如192.168.1.xx），
         然后在手机网页输入Shell控制台输出的本机IP地址即可进入手机端网页控制板子继电器
         
注意事项：ESP32作为服务器，手机或电脑作为客户端

'''

#导入Pin模块
from machine import Pin
import time
import network
import socket

#定义LED控制对象
led1=Pin(15,Pin.OUT,Pin.PULL_DOWN)

#定义继电器控制对象
relay=Pin(25,Pin.OUT) 

#连接的WIFI账号和密码
ssid = "puzhong88"
password = "PUZHONG88"

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
    if relay.value() == 0:
        relay_state = ''
    else:
        relay_state = 'checked'
    html = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>
    body{font-family:Arial; text-align: center; margin: 0px auto; padding-top:30px;}
    .switch{position:relative;display:inline-block;width:120px;height:68px}.switch input{display:none}
    .slider{position:absolute;top:0;left:0;right:0;bottom:0;background-color:#ccc;border-radius:34px}
    .slider:before{position:absolute;content:"";height:52px;width:52px;left:8px;bottom:8px;background-color:#fff;-webkit-transition:.4s;transition:.4s;border-radius:68px}
    input:checked+.slider{background-color:#2196F3}
    input:checked+.slider:before{-webkit-transform:translateX(52px);-ms-transform:translateX(52px);transform:translateX(52px)}
    </style><script>function toggleCheckbox(element) { var xhr = new XMLHttpRequest(); if(element.checked){ xhr.open("GET", "/?relay=on", true); }
    else { xhr.open("GET", "/?relay=off", true); } xhr.send(); }</script></head><body>
    <h1>ESP32 relay control</h1><label class="switch"><input type="checkbox" onchange="toggleCheckbox(this)" %s><span class="slider">
    </span></label></body></html>""" % (relay_state)
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
                relay_on = request.find('/?relay=on')
                relay_off = request.find('/?relay=off')
                if relay_on == 6:
                    print('RELAY ON')
                    relay.value(1)
                if relay_off == 6:
                    print('RELAY OFF')
                    relay.value(0)
                response = web_page()
                client.send('HTTP/1.1 200 OK\n')
                client.send('Content-Type: text/html\n')
                client.send('Connection: close\n\n')
                client.sendall(response)
                client.close()
            except OSError as e:
                conn.close()
                print('Connection closed')
