#ifndef _exti_H
#define _exti_H

#include "public.h"

//定义按键控制管脚
#define key1_pin  14
#define key2_pin  27
#define key3_pin  26
#define key4_pin  25

//变量声明
extern volatile u8 key1_sta;
extern volatile u8 key2_sta;
extern volatile u8 key3_sta;
extern volatile u8 key4_sta;

//函数声明
void exti_init(void);
void key1_isr(void);
void key2_isr(void);
void key3_isr(void);
void key4_isr(void);
#endif
