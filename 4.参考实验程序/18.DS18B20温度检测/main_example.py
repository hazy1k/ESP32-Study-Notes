from machine import Pin
import time
import onewire
import ds18x20

ds18x20 = ds18x20.DS18X20(onewire.OneWire(Pin(13))) # 定义DS18B20控制对象

if __name__ == '__main__':
    roms = ds18x20.scan() # 扫描DS18B20传感器地址
    print("DS18B20 found !")
    while True:
        ds18x20.convert_temp() # 温度转换
        time.sleep(1)
        for rom in roms:
            print("DS18B20 temperature: %.2f °C" % ds18x20.read_temp(rom))
