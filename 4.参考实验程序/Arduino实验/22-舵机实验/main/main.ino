/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：舵机实验
 * 
 * 接线说明：SG90舵机模块-->ESP32 IO
             橙色(信号线)-->(17)
             红色(电源正)-->(5V)
             褐色(电源负)-->(GND)
 * 
 * 实验现象：程序下载成功后，SG90舵机循环以45°步进从0°旋转到180°
 * 
 * 注意事项：
 */

#include "public.h"
#include "pwm.h"


//舵机控制引脚
#define servo_pin  17


//舵机控制
//degree：角度0-180
//返回值：输出对应角度PWM占空比
int servo_ctrl(u8 degree)
{
  const float deadZone=6.4; //对应0.5ms(0.5/(20ms/256))
  const float max=32; //对应2.5ms
  if(degree<0)degree=0;
  else if(degree>180)degree=180;
  return (int)(((max-deadZone)/180)*degree+deadZone);
}

void setup(){
  Serial.begin(115200);
  pwm_init(servo_pin,8,50,8);
  pwm_set_duty(8,servo_ctrl(0));
}
  
void loop(){
  for(u8 i=0;i<=180;i+=45)
  {
    pwm_set_duty(8,servo_ctrl(i));
    delay(1000);
  }
}

