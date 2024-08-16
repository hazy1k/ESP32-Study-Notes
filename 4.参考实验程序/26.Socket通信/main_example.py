from machine import Pin
import time, network, usocket

led1 = Pin(15, Pin.OUT)

ssid = "ssid"
password = "12345678"

dest_ip = "192.168.103.148"
dest_port = 10000

# WIFI连接
def wifi_connect():
    wlan = network.WLAN(network.STA_IF) # STA模式
    wlan.active(True) # 激活接口
    start_time = time.time() # 记录开始时间

    if not wlan.isconnected(): # 如果没有连接过WIFI
        print("WIFI connecting...")
        wlan.connect(ssid, password) # 连接WIFI

        while not wlan.isconnected(): # 等待连接
            led1.value(1)
            time.sleep_ms(500)
            led1.value(0)
            time.sleep_ms(500)

        # 超时判断
            if time.time() - start_time > 15:
                print("WIFI connect timeout!")
                break

    else:
        led1.value(0)
        print("network information:", wlan.ifconfig()) # 打印IP信息    

if __name__ == "__main__":
    if wifi_connect():
        socket = usocket.socket() # 创建socket连接
        addr = (dest_ip, dest_port) # 服务器IP地址和端口
        socket.connect(addr) # 连接服务器
        socket.send("Hello, server!") # 发送数据

        while True:
            text = socket.recv(128) # 接收数据
            if text == None:
                pass
            else:
                print(text) # 打印接收到的数据
                socket.send("I received: " + text.decode("utf-8")) # 发送数据
            time.sleep_ms(100) # 延时100ms
