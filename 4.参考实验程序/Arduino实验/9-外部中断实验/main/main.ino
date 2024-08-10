/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：外部中断实验
 * 
 * 接线说明：按键模块-->ESP32 IO
 *         (K1-K4)-->(14,27,26,25)
 *         
 *         LED模块-->ESP32 IO
 *         (D1-D4)-->(15,2,0,4)
 * 
 * 实验现象：程序下载成功后，操作K1键控制D1指示灯亮灭；操作K2键控制D2指示灯亮灭；
            操作K3键控制D3指示灯亮灭；操作K4键控制D4指示灯亮灭；
 * 
 * 注意事项：
 * 
 */

#include "public.h"
#include "exti.h"


//定义LED控制引脚
#define led1_pin  15
#define led2_pin  2
#define led3_pin  0
#define led4_pin  4

//定义全局变量

void setup() {
  pinMode(led1_pin, OUTPUT);//设置引脚为输出模式
  pinMode(led2_pin, OUTPUT);
  pinMode(led3_pin, OUTPUT);
  pinMode(led4_pin, OUTPUT);
  exti_init();
}

void loop() {
  digitalWrite(led1_pin,key1_sta);
  digitalWrite(led2_pin,key2_sta);
  digitalWrite(led3_pin,key3_sta);
  digitalWrite(led4_pin,key4_sta);
}
