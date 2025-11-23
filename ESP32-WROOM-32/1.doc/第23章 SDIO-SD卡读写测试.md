# 第二十三章 SDIO-SD卡读写测试

## 1. 导入

在数据采集（Data Logger）、图像存储（如 ESP32-CAM）或加载大容量资源（如字体、图片）时，ESP32 内置的 Flash 往往捉襟见肘。  
SD 卡是最佳扩展方案。虽然 MicroPython 支持 SPI 模式驱动 SD 卡，但 ESP32 拥有原生的 **SDMMC 硬件控制器（SDIO）**。

- **SDIO vs SPI**：
  - **SDIO (4-bit)**：使用 4 根数据线并行传输，理论速度极快，占用 CPU 少。
  - **SPI**：使用 1 根数据线，速度受限于 SPI 时钟，且占用 CPU 资源较高。
- **本章目标**：使用 ESP32 的硬件 SDIO 接口挂载 SD 卡，进行文件读写，并进行读写速度基准测试。

---

## 2. 硬件连接与注意事项

ESP32 的 SDIO 接口引脚是固定的（Slot 1），通常对应以下 GPIO。  
**注意**：很多现成的开发板（如 ESP32-CAM）已经板载了 SD 卡槽并连接好了这些线。如果你是自己接线（使用 SD 卡转接板），请务必连接 **上拉电阻**（通常模块上自带 10k-47k 上拉）。

| SD卡引脚   | ESP32 GPIO | 功能  | 备注                   |
| ------- | ---------- | --- | -------------------- |
| **CLK** | GPIO 14    | 时钟  |                      |
| **CMD** | GPIO 15    | 命令  | 需上拉                  |
| **D0**  | GPIO 2     | 数据0 | 也是板载 LED，下载时若被拉低可能失败 |
| **D1**  | GPIO 4     | 数据1 |                      |
| **D2**  | GPIO 12    | 数据2 | **高危引脚** (见下方警告)     |
| **D3**  | GPIO 13    | 数据3 | 也是 CS 功能             |
| **VCC** | 3.3V       | 电源  | **严禁接 5V**           |
| **GND** | GND        | 地   |                      |

> **⚠️ 致命警告（GPIO 12 问题）**：  
> GPIO 12 是 ESP32 的 **MTDI (Bootstrap Pin)**，决定了内部 Flash 的电压（1.8V 或 3.3V）。
> 
> - 如果 SD 卡内部的上拉电阻在启动瞬间把 GPIO 12 拉高，ESP32 可能会认为 Flash 是 1.8V 的，导致无法启动（无限重启）。
> - **解决办法**：如果插着卡无法启动，烧录代码时利用 `efuse` 固化配置，或者**先按住复位键，插卡后再松手**（仅限测试时）。

---

## 3. 基础代码：挂载文件系统

MicroPython 使用 `machine.SDCard` 驱动，并结合 `os` 模块将 SD 卡挂载为一个文件夹（例如 `/sd`）。

```python
import machine
import os

def mount_sd():
    try:
        # 1. 初始化 SD 卡对象
        # slot=1 使用 ESP32 原生 SDMMC 控制器 (SDIO 4-bit)
        # width=4 使用 4线模式 (速度快)，如果硬件只接了 D0，可设为 width=1
        sd = machine.SDCard(slot=1, width=4)

        # 2. 挂载到文件系统
        # 挂载点通常设为 '/sd'
        try:
            os.mount(sd, '/sd')
            print("SD 卡挂载成功！路径: /sd")

            # 打印容量信息
            vfs = os.statvfs('/sd')
            # 块大小 * 总块数 = 总字节
            total_mb = (vfs[0] * vfs[2]) / 1024 / 1024
            free_mb = (vfs[0] * vfs[3]) / 1024 / 1024
            print("总容量: {:.2f} MB".format(total_mb))
            print("剩余容量: {:.2f} MB".format(free_mb))
            return True

        except OSError as e:
            print("挂载失败 (可能已挂载):", e)
            return True # 假设已挂载

    except Exception as e:
        print("SD 卡初始化失败:", e)
        print("请检查接线或确认 SD 卡格式为 FAT32")
        return False

# 执行挂载
mount_sd()
```

---

## 4. 基础读写操作

操作 SD 卡里的文件和操作电脑文件完全一样，使用 Python 标准的 `open()`, `write()`, `read()`。

```python
def test_read_write():
    file_path = '/sd/test_log.txt'

    print("\n=== 开始读写测试 ===")

    # 1. 写入测试 (Write)
    print(f"正在写入文件: {file_path} ...")
    with open(file_path, 'w') as f:
        f.write("Hello ESP32 SDIO!\n")
        f.write("这是一个测试日志。\n")
        f.write("时间戳: 123456789\n")
    print("写入完成。")

    # 2. 追加测试 (Append)
    with open(file_path, 'a') as f:
        f.write("这是追加的一行内容。\n")

    # 3. 读取测试 (Read)
    print("正在读取内容:")
    print("-" * 20)
    with open(file_path, 'r') as f:
        content = f.read()
        print(content.strip())
    print("-" * 20)

    # 4. 列出目录
    print("根目录文件:", os.listdir('/sd'))

# 确保挂载成功后运行
if 'sd' in os.listdir('/'): # 简单检查
    test_read_write()
```

---

## 5. 进阶：SDIO 读写速度基准测试 (Benchmark)

为了验证 SDIO 的性能优势，我们编写一个脚本，写入 1MB 的二进制数据，然后读取，并计算每秒传输速度。

```python
import time
import os

def benchmark_sd(filename='/sd/bench.bin', size_kb=1024, buf_size=4096):
    """
    SD卡速度测试
    :param filename: 测试文件名
    :param size_kb: 测试大小 (KB)
    :param buf_size: 缓冲区大小 (字节)，越大通常越快
    """
    print(f"\n=== 开始速度测试 ({size_kb} KB) ===")

    # 准备数据缓冲区 (全为 0xAA 的假数据)
    chunk = b'\xAA' * buf_size
    chunks_count = (size_kb * 1024) // buf_size

    # --- 写入测试 ---
    start_t = time.ticks_ms()
    with open(filename, 'wb') as f:
        for _ in range(chunks_count):
            f.write(chunk)
    end_t = time.ticks_ms()

    diff = time.ticks_diff(end_t, start_t)
    if diff == 0: diff = 1
    speed_write = (size_kb / 1024) / (diff / 1000)
    print(f"写入耗时: {diff} ms")
    print(f"写入速度: {speed_write:.2f} MB/s")

    # --- 读取测试 ---
    start_t = time.ticks_ms()
    with open(filename, 'rb') as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
    end_t = time.ticks_ms()

    diff = time.ticks_diff(end_t, start_t)
    if diff == 0: diff = 1
    speed_read = (size_kb / 1024) / (diff / 1000)
    print(f"读取耗时: {diff} ms")
    print(f"读取速度: {speed_read:.2f} MB/s")

    # 清理测试文件
    os.remove(filename)
    print("测试文件已删除")

# 运行跑分
benchmark_sd(size_kb=1024) # 测试 1MB
```

**预期结果**：  
在 SDIO 4-bit 模式下，Class 10 的卡通常能达到：

- 写入：300 KB/s ~ 1 MB/s (受限于 Flash 写入机制)
- 读取：800 KB/s ~ 2 MB/s  
  *(注：MicroPython 的文件系统开销较大，无法跑满 SDIO 硬件理论极限，但比 SPI 快得多)*

---

## 6. 实战应用：传感器数据记录仪 (Data Logger)

结合前面的章节，我们可以做一个简单的温湿度+时间记录仪。

```python
import time
import random # 模拟传感器数据

def log_data_loop():
    log_file = '/sd/sensor_data.csv'

    # 如果文件不存在，写入表头
    try:
        os.stat(log_file)
    except OSError:
        with open(log_file, 'w') as f:
            f.write("Timestamp,Temperature,Humidity\n")

    print("开始记录数据 (按 Ctrl+C 停止)...")
    count = 0
    try:
        while True:
            # 模拟获取数据
            temp = 25.0 + random.uniform(-1, 1)
            hum = 60.0 + random.uniform(-5, 5)
            timestamp = time.time()

            # 格式化 CSV 行
            line = "{}, {:.2f}, {:.2f}\n".format(timestamp, temp, hum)

            # 写入文件 (使用 'a' 追加模式)
            with open(log_file, 'a') as f:
                f.write(line)

            print(f"记录 #{count}: {line.strip()}")
            count += 1

            # SD卡写入有磨损，建议使用 flush 或攒一批再写，这里为了演示每条都写
            time.sleep(1)

    except KeyboardInterrupt:
        print("记录停止")

# log_data_loop() 
```

---

## 7. 常见问题排查 (Troubleshooting)

1. **OSError: [Errno 19] ENODEV**：
   - **未检测到 SD 卡**。检查接线，特别是 CMD 和 DATA 线是否有上拉电阻（如果没有，读写极其不稳定）。
   - 检查 SD 卡是否已插入到位。
2. **OSError: timeout waiting for response**：
   - **供电不足**。SD 卡写入瞬间电流很大，确保 ESP32 的 3.3V 电源足够强。
   - SD 卡损坏或不支持。
3. **文件系统无法识别**：
   - MicroPython 默认支持 **FAT32**。
   - 如果你的卡是 64GB 或更大（通常是 exFAT），MicroPython 无法直接挂载。请在电脑上将其格式化为 FAT32（大容量卡需使用 DiskGenius 等工具强制格式化为 FAT32）。
4. **GPIO 12 问题（无限重启）**：
   - 如果插卡后 ESP32 不断重启，拔掉卡就好了，说明 GPIO 12 被卡拉高了。
   - **物理方案**：烧录熔丝（不可逆）将 Flash 电压设为 3.3V。
   - **临时方案**：不要连接 D2 线，改用 `width=1` 模式初始化 `machine.SDCard(slot=1, width=1)`，但这会牺牲速度。

## 8. 小结

SDIO 是 ESP32 处理大文件的核心能力。掌握了 SD 卡挂载，你就不再受限于 ESP32 仅有的 4MB Flash 空间，可以轻松实现长时间的数据记录、播放 WAV 音频或加载大型 GUI 图片资源。下一章，我们将利用这些存储空间，结合 **I2S** 播放音频文件。

---
