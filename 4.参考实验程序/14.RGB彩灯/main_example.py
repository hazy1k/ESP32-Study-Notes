from machine import Pin
from neopixel import NeoPixel
import time

# 定义RGB控制对象
# 控制引脚为16，RGB串联5个
pin = 16
rgb_num = 5
rgb_led = NeoPixel(Pin(pin, Pin.OUT), rgb_num)

# 定义RGB颜色
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
INDIGO = (75, 0, 130)
VIOLET = (138, 43, 226)
COLORS = (RED, ORANGE, YELLOW, GREEN, BLUE, INDIGO, VIOLET)

if __name__ == '__main__':
    while True:
        for color in COLORS:
            for i in range(rgb_num):
                rgb_led[i] = (color[0], color[1], color[2])
                rgb_led.write()
                time.sleep_ms(100)
            time.sleep_ms(1000)    
