#include "step_motor.h"

//端口初始化
void step_motor_init(void)
{
  pinMode(ina_pin, OUTPUT);//设置引脚为输出模式
  pinMode(inb_pin, OUTPUT);
  pinMode(inc_pin, OUTPUT);
  pinMode(ind_pin, OUTPUT);
}

/*******************************************************************************
* 函 数 名       : step_motor_28BYJ48_send_pulse
* 函数功能       : 输出一个数据给ULN2003从而实现向步进电机发送一个脉冲
* 输    入       : step：指定步进序号，可选值0~7
                  dir：方向选择,1：顺时针,0：逆时针
* 输    出       : 无
*******************************************************************************/
void step_motor_28BYJ48_send_pulse(u8 step,u8 dir)
{
  u8 temp=step;
  
  if(dir==0)  //如果为逆时针旋转
    temp=7-step;//调换节拍信号
  switch(temp)//8个节拍控制：A->AB->B->BC->C->CD->D->DA
  {
    case 0: digitalWrite(ina_pin,1);digitalWrite(inb_pin,0);digitalWrite(inc_pin,0);digitalWrite(ind_pin,0);break;
    case 1: digitalWrite(ina_pin,1);digitalWrite(inb_pin,1);digitalWrite(inc_pin,0);digitalWrite(ind_pin,0);break;
    case 2: digitalWrite(ina_pin,0);digitalWrite(inb_pin,1);digitalWrite(inc_pin,0);digitalWrite(ind_pin,0);break;
    case 3: digitalWrite(ina_pin,0);digitalWrite(inb_pin,1);digitalWrite(inc_pin,1);digitalWrite(ind_pin,0);break;
    case 4: digitalWrite(ina_pin,0);digitalWrite(inb_pin,0);digitalWrite(inc_pin,1);digitalWrite(ind_pin,0);break;
    case 5: digitalWrite(ina_pin,0);digitalWrite(inb_pin,0);digitalWrite(inc_pin,1);digitalWrite(ind_pin,1);break;
    case 6: digitalWrite(ina_pin,0);digitalWrite(inb_pin,0);digitalWrite(inc_pin,0);digitalWrite(ind_pin,1);break;
    case 7: digitalWrite(ina_pin,1);digitalWrite(inb_pin,0);digitalWrite(inc_pin,0);digitalWrite(ind_pin,1);break;
    default: digitalWrite(ina_pin,0);digitalWrite(inb_pin,0);digitalWrite(inc_pin,0);digitalWrite(ind_pin,0);break;//停止相序 
  }     
}
