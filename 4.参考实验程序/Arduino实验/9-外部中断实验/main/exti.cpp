#include "exti.h"

volatile u8 key1_sta=0;
volatile u8 key2_sta=0;
volatile u8 key3_sta=0;
volatile u8 key4_sta=0;

//端口初始化
void exti_init(void)
{
  pinMode(key1_pin, INPUT_PULLUP);//设置引脚为输入上拉模式
  pinMode(key2_pin, INPUT_PULLUP);
  pinMode(key3_pin, INPUT_PULLUP);
  pinMode(key4_pin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(key1_pin), key1_isr, FALLING);//设置下降沿触发
  attachInterrupt(digitalPinToInterrupt(key2_pin), key2_isr, FALLING);
  attachInterrupt(digitalPinToInterrupt(key3_pin), key3_isr, FALLING);
  attachInterrupt(digitalPinToInterrupt(key4_pin), key4_isr, FALLING);
}

void key1_isr(void)
{
  key1_sta=!key1_sta;
}

void key2_isr(void)
{
  key2_sta=!key2_sta;
}

void key3_isr(void)
{
  key3_sta=!key3_sta;
}

void key4_isr(void)
{
  key4_sta=!key4_sta;
}

