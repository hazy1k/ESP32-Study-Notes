from machine import Pin
import time
import network

led1 = Pin(15, Pin.OUT)

# 路由器账号密码
ssid = "ssid"
password = "12345678"

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
    wifi_connect() # 连接WIFI
    