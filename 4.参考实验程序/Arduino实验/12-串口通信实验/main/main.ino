/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：串口通信实验
 * 
 * 接线说明：USB转TTL模块-->ESP32 IO
 *         (TXD)-->(16)
           (RXD)-->(17)
           (GND)-->(GND)
 * 
 * 实验现象：程序下载成功后，打开串口调试助手，选择好串口、波特率115200参数等，在串口助手上发送字符数据，
             ESP32串口接收后原封不动返回到串口助手显示
 * 
 * 注意事项：USB转TTL模块上将电源切换为3.3V
 * 
 */

#include "public.h"


//定义全局变量
//定义串口2
HardwareSerial mySerial2(2);
String serialData;


void setup() {
  //串口0配置
  Serial.begin(115200);
  //串口2配置
  //void HardwareSerial::begin(unsigned long baud, uint32_t config=SERIAL_8N1, int8_t rxPin=-1, int8_t txPin=-1, bool invert=false, unsigned long timeout_ms = 20000UL);
  //baud：串口波特率，该值写0则会进入自动侦测波特率程序；
  //config：串口参数，默认SERIAL_8N1为8位数据位、无校验、1位停止位；
  //rxPin：接收管脚针脚号；
  //txPin：发送管脚针脚号；
  //invert：翻转逻辑电平，串口默认高电平为1、低电平为0；
  //timeout_ms：自动侦测波特率超时时间，如果超过该时间还未获得波特率就不会使能串口；
  mySerial2.begin(115200,SERIAL_8N1,16,17);
  
}

void loop() {
  if(Serial.available())  //当串口0接收到信息后
  {
    Serial.println("Serial Data Available..."); // 通过串口监视器通知用户
    serialData=Serial.readString();  // 将接收到的信息使用readString()存储于serialData变量
    Serial.print("Received Serial Data: ");     // 然后通过串口监视器输出serialData变量内容
    Serial.println(serialData);                 // 以便查看serialData变量的信息
  }
  if(mySerial2.available())  //当串口2接收到信息后
  {
    mySerial2.println("Serial2 Data Available..."); // 通过串口监视器通知用户
    serialData=mySerial2.readString();  // 将接收到的信息使用readString()存储于serialData变量
    mySerial2.print("Received Serial2 Data: ");     // 然后通过串口监视器输出serialData变量内容
    mySerial2.println(serialData);                 // 以便查看serialData变量的信息
  }
}
