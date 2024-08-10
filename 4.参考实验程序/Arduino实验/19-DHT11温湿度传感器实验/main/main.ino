/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：DHT11温湿度传感器实验
 * 
 * 接线说明：DHT11温湿度传感器模块-->ESP32 IO
             (VCC)-->(5V)
             (DATA)-->(27)
             (GND)-->(GND)
 * 
 * 实验现象：程序下载成功后，软件串口控制台间隔2S输出DHT11温湿度传感器采集的温度和湿度
 * 
 * 注意事项：
 */

#include "public.h"
#include "dht11.h"

u8 temp;        
u8 humi;
  
void setup(){
  Serial.begin(115200);
  while(DHT11_Init())  //检测是否纯在
  {
    Serial.printf("DHT11 Check Error!\r\n");
    delay(500);    
  }
  Serial.printf("DHT11 Check OK!\r\n");
}

void loop(){
  DHT11_Read_Data(&temp,&humi);
  Serial.printf("温度=%d°C  湿度=%d%%RH\r\n",temp,humi);
  delay(2000);
}

