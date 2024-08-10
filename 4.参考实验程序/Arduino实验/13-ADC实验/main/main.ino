/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：ADC实验
 * 
 * 接线说明：ADC电位器-->ESP32 IO
 *         ADC-->(34)
 * 
 * 实验现象：程序下载成功后，会在软件串口控制台上输出ADC检测电压值，调节电位器可改变检测电压
 * 
 * 注意事项：
 * 
 */

#include "public.h"


//定义全局变量
float adc_vol=0;


void setup() {
  //串口0配置
  Serial.begin(115200);
  
}

void loop() {
  adc_vol=3.3*(float)analogRead(34)/4095;//读取ADC值
  Serial.print("ADC检测电压：");
  Serial.print(adc_vol);
  Serial.println("V");
  delay(500);
}
