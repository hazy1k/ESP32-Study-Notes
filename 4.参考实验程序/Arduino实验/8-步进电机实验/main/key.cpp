#include "key.h"


//端口初始化
void key_init(void)
{
  pinMode(key1_pin, INPUT_PULLUP);//设置引脚为输入上拉模式
  pinMode(key2_pin, INPUT_PULLUP);
  pinMode(key3_pin, INPUT_PULLUP);
  pinMode(key4_pin, INPUT_PULLUP);
}

/*******************************************************************************
* 函 数 名       : key_scan
* 函数功能        : 检测独立按键是否按下，按下则返回对应键值
* 输    入       : mode=0：单次扫描按键
                  mode=1：连续扫描按键
* 输    出       : KEY1_PRESS：K1按下
                  KEY2_PRESS：K2按下
                  KEY3_PRESS：K3按下
                  KEY4_PRESS：K4按下
                  KEY_UNPRESS：未有按键按下
*******************************************************************************/
u8 key_scan(u8 mode)
{
  static u8 key=1;

  if(mode)key=1;//连续扫描按键
  if(key==1&&(digitalRead(key1_pin)==0||digitalRead(key2_pin)==0||digitalRead(key3_pin)==0||digitalRead(key4_pin)==0))//任意按键按下
  {
    delay(10);//消抖
    key=0;
    if(digitalRead(key1_pin)==0)
      return KEY1_PRESS;
    else if(digitalRead(key2_pin)==0)
      return KEY2_PRESS;
    else if(digitalRead(key3_pin)==0)
      return KEY3_PRESS;
    else if(digitalRead(key4_pin)==0)
      return KEY4_PRESS;  
  }
  else if(digitalRead(key1_pin)==1&&digitalRead(key2_pin)==1&&digitalRead(key3_pin)==1&&digitalRead(key4_pin)==1) //无按键按下
  {
    key=1;      
  }
  return KEY_UNPRESS;   
}
