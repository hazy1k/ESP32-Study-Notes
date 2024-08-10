/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：DS18B20温度传感器实验
 * 
 * 接线说明：DS18B20温度传感器模块-->ESP32 IO
            (DS)-->(13)
 * 
 * 实验现象：程序下载成功后，软件串口控制台间隔1S输出DS18B20温度传感器采集的温度
 * 
 * 注意事项：需要在软件中选择"项目"-->"加载库"-->"添加一个.ZIP库..."-->选择到本实验目录下的两个压缩文件包“OneWire-master.zip”和“Arduino-Temperature-Control-Library-master.zip”安装即可。
 *          该库使用方法可参考：https://blog.csdn.net/Naisu_kun/article/details/88420357
 */

#include "public.h"
#include <DallasTemperature.h>

#define ONE_WIRE_BUS    13 //1-wire数据总线连接
OneWire oneWire(ONE_WIRE_BUS); //声明
DallasTemperature sensors(&oneWire); //声明

void setup(){
  Serial.begin(115200);
  sensors.begin();
}

void loop(){
  Serial.println("发起温度转换");
  sensors.requestTemperatures(); //向总线上所有设备发送温度转换请求，默认情况下该方法会阻塞
  Serial.println("温度转换完成");

  float tempC = sensors.getTempCByIndex(0); //获取索引号0的传感器摄氏温度数据
  if (tempC != DEVICE_DISCONNECTED_C) //如果获取到的温度正常
  {
    Serial.print("当前温度是： ");
    Serial.print(tempC);
    Serial.println(" ℃\n");
  }
  delay(2000);
}

