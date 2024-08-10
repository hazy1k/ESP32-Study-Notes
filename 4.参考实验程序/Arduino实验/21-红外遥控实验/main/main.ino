/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：红外遥控实验
 * 
 * 接线说明：红外接收模块-->ESP32 IO
            (IR)-->(14)
 * 
 * 实验现象：程序下载成功后，当按下遥控器键时，软件串口控制台输出红外遥控器控制码（十六进制数）
 * 
 * 注意事项：需要在软件中选择"项目"-->"加载库"-->"添加一个.ZIP库..."-->选择到本实验目录下的1个压缩文件包“IRremoteESP8266-master.zip”安装即可。
 *          该库使用方法可参考：压缩包解压后可查看examples使用。
 */

#include "public.h"
#include <IRremoteESP8266.h>
#include <IRrecv.h>
#include <IRutils.h>

//红外控制引脚
#define kRecvPin  14
IRrecv irrecv(kRecvPin);
decode_results results;

void setup(){
  Serial.begin(115200);
  irrecv.enableIRIn();
  
}
  
void loop(){
  if (irrecv.decode(&results)) 
  {
    // print() & println() can't handle printing long longs. (uint64_t)
    serialPrintUint64(results.value, HEX);
    Serial.println("");
    irrecv.resume();  // Receive the next value
  }
  delay(100);
}

