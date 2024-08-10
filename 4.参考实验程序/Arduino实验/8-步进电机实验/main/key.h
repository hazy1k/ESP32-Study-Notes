#ifndef _key_H
#define _key_H

#include "public.h"

//定义按键控制管脚
#define key1_pin  14
#define key2_pin  27
#define key3_pin  26
#define key4_pin  25

//使用宏定义独立按键按下的键值
#define KEY1_PRESS  1
#define KEY2_PRESS  2
#define KEY3_PRESS  3
#define KEY4_PRESS  4
#define KEY_UNPRESS 0 

//函数声明
void key_init(void);
u8 key_scan(u8 mode);

#endif
