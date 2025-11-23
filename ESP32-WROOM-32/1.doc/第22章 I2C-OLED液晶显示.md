# 第二十二章 I2C-OLED 液晶显示

## 1. 完整的 MicroPython 驱动库

请将以下完整代码保存为 `ssd1306.py` 并上传到 ESP32。它包含底层的命令处理和 I2C 通信封装。

```python
# 文件名: ssd1306.py
from micropython import const
import framebuf

# 寄存器定义
SET_CONTRAST        = const(0x81)
SET_ENTIRE_ON       = const(0xa4)
SET_NORM_INV        = const(0xa6)
SET_DISP            = const(0xae)
SET_MEM_ADDR        = const(0x20)
SET_COL_ADDR        = const(0x21)
SET_PAGE_ADDR       = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP       = const(0xa0)
SET_MUX_RATIO       = const(0xa8)
SET_COM_OUT_DIR     = const(0xc0)
SET_DISP_OFFSET     = const(0xd3)
SET_COM_PIN_CFG     = const(0xda)
SET_DISP_CLK_DIV    = const(0xd5)
SET_PRECHARGE       = const(0xd9)
SET_VCOM_DESEL      = const(0xdb)
SET_CHARGE_PUMP     = const(0x8d)

class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def init_display(self):
        for cmd in (
            SET_DISP | 0x00, # off
            SET_MEM_ADDR, 0x00, # horizontal
            SET_DISP_START_LINE | 0x00,
            SET_SEG_REMAP | 0x01, # column addr 127 mapped to SEG0
            SET_MUX_RATIO, self.height - 1,
            SET_COM_OUT_DIR | 0x08, # scan from COM[N] to COM0
            SET_DISP_OFFSET, 0x00,
            SET_COM_PIN_CFG, 0x02 if self.height == 32 else 0x12,
            SET_DISP_CLK_DIV, 0x80,
            SET_PRECHARGE, 0x22 if self.external_vcc else 0xf1,
            SET_VCOM_DESEL, 0x30, # 0.83*Vcc
            SET_CONTRAST, 0xff, # maximum
            SET_ENTIRE_ON, # output follows RAM contents
            SET_NORM_INV, # not inverted
            SET_CHARGE_PUMP, 0x10 if self.external_vcc else 0x14,
            SET_DISP | 0x01): # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        self.write_cmd(SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            x0 += 32
            x1 += 32
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)

    def write_cmd(self, cmd):
        raise NotImplementedError

    def write_data(self, buf):
        raise NotImplementedError

class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3c, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        # Add an extra byte to the data buffer to hold an I2C data/command byte
        # to act as a register address.
        self.write_list = [b'\x40', None] 
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80 # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)
```

---

## 2. 基础实战：Hello World 与 几何图形

MicroPython 的 SSD1306 库继承自 `framebuf`，这意味着我们不仅能显示文字，还能直接画点、线、矩形。

**代码示例：**

```python
from machine import Pin, SoftI2C
import ssd1306
import time

# 1. 初始化 I2C (ESP32)
# SCL -> GPIO 22, SDA -> GPIO 21
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)

# 2. 扫描设备（可选，用于检查接线）
devices = i2c.scan()
if len(devices) == 0:
    print("未找到 OLED 设备，请检查接线！")
else:
    print("发现 OLED 设备地址: 0x{:02x}".format(devices[0]))

# 3. 创建 OLED 对象 (128x64)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# 4. 绘图测试
oled.fill(0)  # 清屏 (0=黑色, 1=白色)

# 写文字 (不支持中文，仅 ASCII)
oled.text("ESP32 OLED", 0, 0)      # (内容, x, y)
oled.text("MicroPython", 0, 10)

# 画矩形
oled.rect(0, 25, 128, 20, 1)       # (x, y, w, h, color) 空心矩形
oled.fill_rect(2, 27, 50, 16, 1)   # 实心矩形

# 画线
oled.line(0, 50, 127, 63, 1)       # (x1, y1, x2, y2, color)

# 画点
oled.pixel(64, 32, 1)              # (x, y, color)

# 5. 必须调用 show() 才能将显存发送到屏幕
oled.show()
```

---

## 3. 进阶实战：动态弹球动画

OLED 刷新率很快，配合 ESP32 的双核高性能，可以制作流畅的动画。

**核心逻辑**：

1. `oled.fill(0)` 清空缓冲区。
2. 计算新坐标。
3. 绘制图形。
4. `oled.show()` 刷新。
5. 短暂延时。

```python
import time
import random

# 假设 i2c 和 oled 已经初始化

x, y = 64, 32   # 初始位置
vx, vy = 2, 2   # 速度
r = 3           # 半径

try:
    while True:
        # 1. 清除上一帧
        oled.fill(0)

        # 2. 计算物理运动
        x += vx
        y += vy

        # 3. 碰撞检测（碰到边界反弹）
        if x <= r or x >= 128 - r:
            vx = -vx
        if y <= r or y >= 64 - r:
            vy = -vy

        # 4. 绘制球体 (用实心矩形模拟，因为 framebuf 自带没有圆)
        # 如果你想画圆，需要自己写算法，或者用 fill_rect 近似
        oled.fill_rect(x-r, y-r, r*2, r*2, 1)

        # 绘制边框
        oled.rect(0, 0, 128, 64, 1)

        # 5. 刷新屏幕
        oled.show()

        # 6. 控制帧率
        time.sleep_ms(20) # 约 50fps

except KeyboardInterrupt:
    print("动画停止")
```

---

## 4. 专家级：如何显示中文？

MicroPython 默认固件**不支持**中文字库（因为字库太大，且编码复杂）。要在 OLED 上显示中文，通常有两种方法：

### 方法一：取模法（适合只有几个固定汉字的场景）

使用“PCtoLCD2002”等取模软件，将汉字转换为 16x16 的点阵数据（字节数组），然后画到屏幕上。

**示例：显示“你好”**  
*假设取模格式为：阴码、逐列式、顺向（根据软件设置调整）*

```python
# 简单的绘制函数，将 16x16 的 buffer 画到指定位置 (x, y)
# 这是一个简化的 demo，实际需要配合取模软件生成的具体 buffer
def draw_chinese_char(oled, x, y, bitmap):
    # bitmap 应该是一个 32 字节的数组 (16x16像素 -> 256位 -> 32字节)
    # 这里需要根据你的取模软件格式来编写解析逻辑
    # Framebuf 提供了一个简单的方法：blit
    import framebuf
    # 创建一个临时的 framebuf 对象来容纳这个汉字
    # MONO_VLSB 是大多数取模软件的常用格式
    fb = framebuf.FrameBuffer(bytearray(bitmap), 16, 16, framebuf.MONO_VLSB)
    oled.blit(fb, x, y)

# "你" 的 16x16 点阵数据 (示例数据)
ni_bitmap = bytearray([
    0x00,0x80,0x60,0xF8,0x07,0x40,0x20,0x18,0x0F,0x08,0xC8,0x08,0x08,0x28,0x18,0x00,
    0x01,0x00,0x00,0xFF,0x00,0x10,0x0C,0x03,0x00,0x00,0x1F,0x00,0x00,0x00,0x00,0x00
])

# 清屏
oled.fill(0)
# 在 (10, 10) 处画 "你"
draw_chinese_char(oled, 10, 10, ni_bitmap)
oled.show()
```

### 方法二：使用带字库的固件或外部字库

对于需要显示任意汉字的项目，建议使用 **u8g2** 库的 MicroPython 移植版，或者烧录集成了中文字库的定制固件。这超出了本章的基础范围，但如果你有需求，可以在后续章节深入。

---

## 5. 常见问题与排查

1. **I2C 地址错误**：
   
   - 通常为 `0x3c`。
   - 有些模块背面有电阻跳线，跳到另一边会变成 `0x3d`。请务必使用 `i2c.scan()` 确认。

2. **屏幕花屏 / 噪点**：
   
   - 通常是 `SoftI2C` 频率太高或线太长。尝试将 `freq=400000` 降为 `100000`。
   - 检查 GND 是否接触良好。

3. **显示内容错位**：
   
   - 市面上有 0.96寸 和 1.3寸 两种 OLED，外观很像。1.3寸通常使用 SH1106 驱动，指令集略有不同，用 SSD1306 驱动会出现第一列像素偏移。

## 6. 小结

本章我们掌握了 OLED 的底层驱动、基础绘图 API 和动态刷新技巧。结合上一章的超声波或舵机，你现在可以做一个 **“可视化雷达”** 了——用舵机转动超声波，OLED 屏幕上画出扫描到的障碍物距离，这才是嵌入式开发的乐趣所在！

---
