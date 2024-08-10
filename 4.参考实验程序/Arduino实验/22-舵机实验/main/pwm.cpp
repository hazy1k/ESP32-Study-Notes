#include "pwm.h"

//PWM初始化
//pin：引脚号
//chanel：PWM输出通道0-15，0-7高速通道，由80M时钟驱动，8-15低速通道，有1M时钟驱动
//freq：PWM输出频率，单位HZ
//resolution：PWM占空比的分辨率1-16，比如设置8，分辨率范围0-255
void pwm_init(u8 pin,u8 chanel,u8 freq,u8 resolution)
{
  ledcSetup(chanel, freq, resolution);// PWM初始化
  ledcAttachPin(pin, chanel);// 绑定PWM通道到GPIO上
}

//PWM占空比设置
void pwm_set_duty(u8 chanel,u16 duty)
{
  ledcWrite(chanel,duty);// 改变PWM的占空比
}
