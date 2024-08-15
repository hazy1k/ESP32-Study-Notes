#导入Pin模块
import machine, sdcard, os
from machine import SPI, Pin

sd = sdcard.SDCard(SPI(2, sck=Pin(18), mosi=Pin(23), miso=Pin(19)), Pin(4))
os.mount(sd,"/sd")

print(os.listdir("/sd"))

file_name="/sd/EBOOK/text.txt"

f=open(file_name,"w")  #打开文件，进行写操作
write_txt="大家好，欢迎使用普中-ESP32开发板，人生苦短，我选Python和MicroPython"
print(f.write(write_txt))  #写入
f.close()  #关闭文件

f=open(file_name)  #打开文件，进行读操作
read_txt=f.read()
print(read_txt)
f.close()  #关闭文件

#程序入口
if __name__=="__main__":
    
    while True:
        pass
