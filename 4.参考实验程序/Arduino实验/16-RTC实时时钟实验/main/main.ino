/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：RTC实时时钟实验
 * 
 * 接线说明：
 * 
 * 实验现象：程序下载成功后，软件串口控制台间隔1S输出RTC实时时钟年月日时分秒星期
 * 
 * 注意事项：需要在软件中选择"项目"-->"加载库"-->"管理库"-->输入"ESP32Time"安装即可。
 * 
 */

#include "public.h"
#include <ESP32Time.h>

ESP32Time rtc(3600);  // offset in seconds GMT+1

void setup(){
  Serial.begin(115200);
  rtc.setTime(30, 24, 15, 17, 9, 2022);//2022年9月17日15点24分30秒
}

void loop(){
  //  Serial.println(rtc.getTime());          //  (String) 15:24:38
  //  Serial.println(rtc.getDate());          //  (String) Sun, Jan 17 2021
  //  Serial.println(rtc.getDate(true));      //  (String) Sunday, January 17 2021
  //  Serial.println(rtc.getDateTime());      //  (String) Sun, Jan 17 2021 15:24:38
  //  Serial.println(rtc.getDateTime(true));  //  (String) Sunday, January 17 2021 15:24:38
  //  Serial.println(rtc.getTimeDate());      //  (String) 15:24:38 Sun, Jan 17 2021
  //  Serial.println(rtc.getTimeDate(true));  //  (String) 15:24:38 Sunday, January 17 2021
  //
  //  Serial.println(rtc.getMicros());        //  (long)    723546
  //  Serial.println(rtc.getMillis());        //  (long)    723
  //  Serial.println(rtc.getEpoch());         //  (long)    1609459200
  //  Serial.println(rtc.getSecond());        //  (int)     38    (0-59)
  //  Serial.println(rtc.getMinute());        //  (int)     24    (0-59)
  //  Serial.println(rtc.getHour());          //  (int)     3     (0-12)
  //  Serial.println(rtc.getHour(true));      //  (int)     15    (0-23)
  //  Serial.println(rtc.getAmPm());          //  (String)  pm
  //  Serial.println(rtc.getAmPm(true));      //  (String)  PM
  //  Serial.println(rtc.getDay());           //  (int)     17    (1-31)
  //  Serial.println(rtc.getDayofWeek());     //  (int)     0     (0-6)
  //  Serial.println(rtc.getDayofYear());     //  (int)     16    (0-365)
  //  Serial.println(rtc.getMonth());         //  (int)     0     (0-11)
  //  Serial.println(rtc.getYear());          //  (int)     2021
  
  //  Serial.println(rtc.getLocalEpoch());         //  (long)    1609459200 epoch without offset

  Serial.println(rtc.getTime("%A, %B %d %Y %H:%M:%S"));   // (String) returns time with specified format 
  // formating options  http://www.cplusplus.com/reference/ctime/strftime/
  delay(1000);
}

