'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：WIFI远程控制--DHT11温湿度采集
接线说明：LED模块-->ESP32 IO
         (D1)-->(15)
         
         DS18B20温度传感器模块-->ESP32 IO
         (DS)-->(13)
         
实验现象：程序下载成功后，手机连接的WIFI需和ESP32连接的WIFI处于同一频段（比如192.168.1.xx），
         然后在手机网页输入Shell控制台输出的本机IP地址即可进入手机端网页显示采集的温度数据，
         可手动刷新页面更新数据显示。
         
注意事项：ESP32作为服务器，手机或电脑作为客户端

'''

#导入Pin模块
from machine import Pin
import time
import network
import socket
import onewire
import ds18x20

#定义LED控制对象
led1=Pin(15,Pin.OUT,Pin.PULL_DOWN)

#定义DS18B20控制对象
ds18b20=ds18x20.DS18X20(onewire.OneWire(Pin(13)))

#连接的WIFI账号和密码
ssid = "PRECHIN"
password = "12345678"


def read_ds_sensor():
    roms = ds18b20.scan()
    print('Found DS devices: ', roms)
    print('Temperatures: ')
    ds18b20.convert_temp()
    for rom in roms:
        temp = ds18b20.read_temp(rom)
        if isinstance(temp, float):
            msg = round(temp, 2)
            print(temp, end=' ')
            print('Valid temperature')
            return msg
    return b'0.0'
        
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
  temp = read_ds_sensor()
  html = """<!DOCTYPE HTML><html><head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.7.2/css/all.css" integrity="sha384-fnmOCqbTlWIlj8LyTjo7mOUStjsKC4pOpQbqyi7RrhN7udi9RwhKkMHpvLbHG9Sr" crossorigin="anonymous">
  <style> html { font-family: Arial; display: inline-block; margin: 0px auto; text-align: center; }
    h2 { font-size: 3.0rem; } p { font-size: 3.0rem; } .units { font-size: 1.2rem; } 
    .ds-labels{ font-size: 1.5rem; vertical-align:middle; padding-bottom: 15px; }
  </style></head><body><h2>ESP32 DS18B20 Temperature detection</h2>
  <p><i class="fas fa-thermometer-half" style="color:#059e8a;"></i> 
    <span class="ds-labels">Temperature</span>
    <span id="temperature">""" + str(temp) + """</span>
    <sup class="units">&deg;C</sup>
  </p>
    <p><i class="fas fa-thermometer-half" style="color:#059e8a;"></i> 
    <span class="ds-labels">Temperature</span>
    <span id="temperature">""" + str(round(temp * (9/5) + 32.0, 2)) + """</span>
    <sup class="units">&deg;F</sup>
  </p></body></html>"""
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


