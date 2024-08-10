#ifndef _step_motor_H
#define _step_motor_H

#include "public.h"

//定义步进电机控制管脚
#define ina_pin   15
#define inb_pin   2
#define inc_pin   0
#define ind_pin   4

// 定义步进电机速度，值越小，速度越快
// 最小不能小于1
#define STEPMOTOR_MAXSPEED        1  
#define STEPMOTOR_MINSPEED        5 


//函数声明
void step_motor_init(void);
void step_motor_28BYJ48_send_pulse(u8 step,u8 dir);

#endif
