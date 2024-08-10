/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：DS1302实时时钟实验
 * 
 * 接线说明：DS1302时钟模块-->ESP32 IO
           (CE)-->(23)
           (IO)-->(19)
           (CK)-->(18)
 * 
 * 实验现象：程序下载成功后，软件串口控制台间隔1S输出DS1302实时时钟年月日时分秒星期
 * 
 * 注意事项：需要在软件中选择"项目"-->"加载库"-->"管理库"-->输入"RTCLib by NeiroN"安装即可。
 *            API函数使用参考https://github.com/NeiroNx/RTCLib
 * 
 */

#include "public.h"
#include <RTClib.h>

DS1302 rtc(23, 18, 19);

char buf[20];

void setup(){
  Serial.begin(115200);
  rtc.begin();
  if (!rtc.isrunning()) 
  {
    Serial.println("RTC is NOT running!");
    // following line sets the RTC to the date & time this sketch was compiled
    rtc.adjust(DateTime(__DATE__, __TIME__));
  }
  rtc.adjust(DateTime(__DATE__, __TIME__));
}

void loop(){
  DateTime now = rtc.now();
  Serial.println(now.tostr(buf));
  delay(1000);
}

