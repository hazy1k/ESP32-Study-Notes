'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：蓝牙控制舵机
接线说明：LED模块-->ESP32 IO
         (D1)-->(15)
         
         KEY模块-->ESP32 IO
         (K1)-->(14)
         
         SG90舵机模块-->ESP32 IO
         橙色(信号线)-->(17)
         红色(电源正)-->(5V)
         褐色(电源负)-->(GND)
         
实验现象：程序下载成功后，软件shell控制台输出蓝牙BLE名称“ESP32BLE”，D1指示灯快闪，等待APP蓝牙连接。
         安卓手机系统，打开应用市场，搜索“BLE蓝牙调试助手”下载，打开该APP，选择蓝牙名称为“ESP32BLE”
         连接，然后按照实验现象操作即可。
         
注意事项：

'''

#导入Pin模块
from machine import Pin
from machine import Timer
from time import sleep_ms
import bluetooth
from servo import Servo


BLE_MSG = ""


class ESP32_BLE():
    def __init__(self, name):
        self.led = Pin(15, Pin.OUT)
        self.timer1 = Timer(0)
        self.name = name
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.config(gap_name=name)
        self.disconnected()
        self.ble.irq(self.ble_irq)
        self.register()
        self.ble.gatts_write(self.rx, bytes(100))  #修改一次最大接收字节数100
        self.advertiser()

    def connected(self):
        self.led.value(1)
        self.timer1.deinit()

    def disconnected(self):        
        self.timer1.init(period=100, mode=Timer.PERIODIC, callback=lambda t: self.led.value(not self.led.value()))

    def ble_irq(self, event, data):
        global BLE_MSG
        if event == 1: #_IRQ_CENTRAL_CONNECT 手机链接了此设备
            self.connected()
        elif event == 2: #_IRQ_CENTRAL_DISCONNECT 手机断开此设备
            self.advertiser()
            self.disconnected()
        elif event == 3: #_IRQ_GATTS_WRITE 手机发送了数据 
            buffer = self.ble.gatts_read(self.rx)
            BLE_MSG = buffer.decode('UTF-8').strip()
            
    def register(self):        
        service_uuid = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
        reader_uuid = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
        sender_uuid = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'

        services = (
            (
                bluetooth.UUID(service_uuid), 
                (
                    (bluetooth.UUID(sender_uuid), bluetooth.FLAG_NOTIFY), 
                    (bluetooth.UUID(reader_uuid), bluetooth.FLAG_WRITE),
                )
            ), 
        )

        ((self.tx, self.rx,), ) = self.ble.gatts_register_services(services)

    def send(self, data):
        self.ble.gatts_notify(0, self.tx, data + '\n')

    def advertiser(self):
        name = bytes(self.name, 'UTF-8')
        adv_data = bytearray('\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name
        self.ble.gap_advertise(100, adv_data)
        print(adv_data)
        print("\r\n")


def buttons_irq(pin):
    led.value(not led.value())
    print('LED is ON.' if led.value() else 'LED is OFF')
    ble.send('LED is ON.' if led.value() else 'LED is OFF')


if __name__ == "__main__":
    ble = ESP32_BLE("ESP32BLE")

    but = Pin(14, Pin.IN)
    but.irq(trigger=Pin.IRQ_FALLING, handler=buttons_irq)

    led = Pin(15, Pin.OUT)
    
    #定义SG90舵机控制对象
    my_servo = Servo(Pin(17))
    my_servo.write_angle(0)  #角度0°

    while True:
        if BLE_MSG == 'read_LED':
            print(BLE_MSG)
            BLE_MSG = ""
            print('LED is ON.' if led.value() else 'LED is OFF')
            ble.send('LED is ON.' if led.value() else 'LED is OFF')
        elif BLE_MSG:
            print("接收到的信息：>>%s<<" % BLE_MSG)
            my_servo.write_angle(int(BLE_MSG))  #角度控制
        sleep_ms(100)


            
