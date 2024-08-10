/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：定时器中断实验
 * 
 * 接线说明：LED模块-->ESP32 IO
 *         (D1)-->(15)
 * 
 * 实验现象：程序下载成功后，D1指示灯间隔0.5s状态翻转
 * 
 * 注意事项：
 * 
 */

#include "public.h"
#include "led.h"
#include "time.h"


//定义全局变量


void setup() {
  led_init();
  time0_init(500000);//定时500ms
  
}

void loop() {
  
}
