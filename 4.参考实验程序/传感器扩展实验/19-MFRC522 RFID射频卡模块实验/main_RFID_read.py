'''
深圳市普中科技有限公司（PRECHIN 普中）
技术支持：www.prechin.net
PRECHIN
 普中

实验名称：MFRC522 RFID射频卡模块实验
接线说明：MFRC522 RFID射频卡模块-->ESP32 IO
         NSS-->5
         SCK-->18
         MOSI-->23
         MISO-->19
         3.3V-->3V3
         GND-->GND
         
实验现象：程序下载成功后，使用持卡感应后，在Shell控制台输出对应的ID

注意事项：

'''

from time import sleep_ms
from machine import Pin, SoftSPI
from mfrc522 import MFRC522


sck = Pin(18, Pin.OUT)
mosi = Pin(23, Pin.OUT)
miso = Pin(19, Pin.OUT)
spi = SoftSPI(baudrate=100000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

sda = Pin(5, Pin.OUT)


def do_read():
    try:
        while True:
            rdr = MFRC522(spi, sda)
            uid = ""
            (stat, tag_type) = rdr.request(rdr.REQIDL)
            if stat == rdr.OK:
                (stat, raw_uid) = rdr.anticoll()
                if stat == rdr.OK:
                    print("New card detected")
                    print("  - tag type: 0x%02x" % tag_type)
                    uid = ("0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]))
                    print(uid)
                    if rdr.select_tag(raw_uid) == rdr.OK:
                        key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                        
                        if rdr.auth(rdr.AUTHENT1A, 8, key, raw_uid) == rdr.OK:
                            print("Address 8 data: %s" % rdr.read(8))
                            rdr.stop_crypto1()
                        else:
                            print("Authentication error")
                    else:
                        print("Failed to select tag")                   
                        
                    sleep_ms(100)
    except KeyboardInterrupt:
        print("Bye")

# 程序入口
if __name__ == '__main__':
    do_read() # 读取成功，返回卡片类型和ID
