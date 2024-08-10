/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：步进电机实验
 * 
 * 接线说明：电机模块-->ESP32 IO
 *         (IN1-IN4)-->(15,2,0,4)
 *         
 *         电机模块输出-->28BYJ-48步进电机
 *         (5V)-->红线
 *         (O1)-->依次排序
 *         
 *         按键模块-->ESP32 IO
 *         (K1-K4)-->(14,27,26,25)
 * 
 * 实验现象：程序下载成功后，当按下KEY1键可调节电机旋转方向；当按下KEY2键，电机加速；
            当按下KEY3键，电机减速；
 * 
 * 注意事项：
 * 
 */

#include "public.h"
#include "key.h"
#include "step_motor.h"


//定义全局变量
u8 g_key=0;
u8 g_dir=0;//默认逆时针方向
u8 g_speed=STEPMOTOR_MAXSPEED;//默认最大速度旋转
u8 g_step=0;

void setup() {
  key_init();
  step_motor_init();
}

void loop() {
  g_key=key_scan(0);
  if(g_key==KEY1_PRESS)//换向
  {
    g_dir=!g_dir;    
  }
  else if(g_key==KEY2_PRESS)//加速
  {
    if(g_speed>STEPMOTOR_MAXSPEED)
      g_speed-=1;     
  }
  else if(g_key==KEY3_PRESS)//减速
  {
    if(g_speed<STEPMOTOR_MINSPEED)
      g_speed+=1;     
  }
  step_motor_28BYJ48_send_pulse(g_step++,g_dir);
  if(g_step==8)g_step=0;    
  delay(g_speed);
}
