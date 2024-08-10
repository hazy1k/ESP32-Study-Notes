#ifndef _pwm_H
#define _pwm_H

#include "public.h"


//函数声明
void pwm_init(u8 pin,u8 chanel,u8 freq,u8 resolution);
void pwm_set_duty(u8 chanel,u16 duty);

#endif
