/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：超声波测距实验
 * 
 * 接线说明：HC-SR04超声波模块-->ESP32 IO
             (VCC)-->(5V)
             (Trig)-->(4)
             (Echo)-->(27)
             (GND)-->(GND)
 * 
 * 实验现象：程序下载成功后，软件串口控制台间隔一段时间输出超声波模块测量距离
 * 
 * 注意事项：需要在软件中选择"项目"-->"加载库"-->"添加一个.ZIP库..."-->选择到本实验目录下的1个压缩文件包“HCSR04-master.zip”安装即可。
 *          该库使用方法可参考：https://github.com/Teknologiskolen/HCSR04/commits?author=theresetmaster
 */

#include "public.h"
#include <afstandssensor.h>

// AfstandsSensor(triggerPin, echoPin);
AfstandsSensor afstandssensor(4, 27);
  
void setup(){
  Serial.begin(115200);
  
}

void loop(){
  Serial.printf("测量距离：%.2fCM\r\n",afstandssensor.afstandCM());
  delay(500);
}

