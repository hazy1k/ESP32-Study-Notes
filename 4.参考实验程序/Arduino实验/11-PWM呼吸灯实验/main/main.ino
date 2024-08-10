/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：PWM呼吸灯实验
 * 
 * 接线说明：LED模块-->ESP32 IO
 *         (D1)-->(15)
 * 
 * 实验现象：程序下载成功后，D1指示灯呈现呼吸灯效果，由暗变亮，再由亮变暗
 * 
 * 注意事项：
 * 
 */

#include "public.h"
#include "led.h"
#include "pwm.h"


//定义全局变量
u16 g_duty_value=0;
u8 g_fx=1;

void setup() {
  pwm_init(led1_pin,0,1000,10);
  
}

void loop() {
  if(g_fx==1)
  {
    g_duty_value+=10;
    if(g_duty_value>1010)g_fx=0;
  }
  else
  {
    g_duty_value-=10;
    if(g_duty_value<10)g_fx=1;
  }
  pwm_set_duty(0,g_duty_value);
  delay(10);
}
