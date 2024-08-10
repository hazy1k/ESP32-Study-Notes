/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：蓝牙实验--控制LED
 * 
 * 接线说明：LED模块-->ESP32 IO
 *          D1-->15
            
 * 
 * 实验现象：程序下载成功后，手机预先安装工程目录下“蓝牙串口调试助手.apk”，打开软件，连接蓝牙名称为“ESP32test”，然后发送字符串“on”和"off"
            开关LED指示灯。
 * 
 * 注意事项：
 */

#include "public.h"
#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

#if !defined(CONFIG_BT_SPP_ENABLED)
#error Serial Bluetooth not available or not enabled. It is only available for the ESP32 chip.
#endif

BluetoothSerial SerialBT;

//定义LED1管脚
#define LED1 15

char buf[9];

void setup() {
  Serial.begin(115200);
  SerialBT.begin("ESP32test"); //Bluetooth device name
  Serial.println("The device started, now you can pair it with bluetooth!");
  //设置LED1引脚为输出模式
  pinMode(LED1, OUTPUT);
}

void loop() {
  if (Serial.available()) {
    SerialBT.write(Serial.read());
  }
  if (SerialBT.available()) {
    // Serial.write(SerialBT.read());
    for(u8 i=0;i<9;i++)
    {
      buf[i]=SerialBT.read();  
      Serial.print(buf[i]); //串口输出蓝牙接收数据   
    }
    if(buf[0]=='o' && buf[1]=='n') 
      digitalWrite(LED1, HIGH);//LED1引脚输出高电平，点亮
    else if(buf[0]=='o' && buf[1]=='f' && buf[2]=='f')
      digitalWrite(LED1, LOW);//LED1引脚输出低电平，熄灭                     
  }
  delay(20);
}
