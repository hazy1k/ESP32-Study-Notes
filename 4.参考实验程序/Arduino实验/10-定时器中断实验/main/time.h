#ifndef _time_H
#define _time_H

#include "public.h"

//变量声明
extern hw_timer_t *timer0;

//函数声明
void time0_init(u32 per);
void time0_isr(void);

#endif
