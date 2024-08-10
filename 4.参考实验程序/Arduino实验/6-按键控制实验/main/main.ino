/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：按键控制实验
 * 
 * 接线说明：按键模块-->ESP32 IO
 *         (K1-K4)-->(14,27,26,25)
 *         
 *         LED模块-->ESP32 IO
 *         (D1-D4)-->(15,2,0,4)
 * 
 * 实验现象：程序下载成功后，操作K1键控制D1指示灯亮灭；操作K2键控制D2指示灯亮灭；
           操作K3键控制D3指示灯亮灭；操作K4键控制D4指示灯亮灭；
 * 
 * 注意事项：
 * 
 */

//定义按键控制管脚
#define key1_pin  14 
#define key2_pin  27
#define key3_pin  26
#define key4_pin  25
//定义LED控制管脚
#define led1_pin  15
#define led2_pin  2
#define led3_pin  0
#define led4_pin  4

//类型重定义
typedef unsigned char u8;
typedef unsigned int u16;

//定义全局变量
u8 g_key=0;
u8 g_led1_sta=0;
u8 g_led2_sta=0;
u8 g_led3_sta=0;
u8 g_led4_sta=0;

//使用宏定义独立按键按下的键值
#define KEY1_PRESS  1
#define KEY2_PRESS  2
#define KEY3_PRESS  3
#define KEY4_PRESS  4
#define KEY_UNPRESS 0 

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

void setup() {
  pinMode(key1_pin, INPUT_PULLUP);//设置引脚为输入上拉模式
  pinMode(key2_pin, INPUT_PULLUP);
  pinMode(key3_pin, INPUT_PULLUP);
  pinMode(key4_pin, INPUT_PULLUP);

  pinMode(led1_pin, OUTPUT);//设置引脚为输出模式
  pinMode(led2_pin, OUTPUT);
  pinMode(led3_pin, OUTPUT);
  pinMode(led4_pin, OUTPUT);

  digitalWrite(led1_pin,0);//引脚输出低电平
  digitalWrite(led2_pin,0);//引脚输出低电平
  digitalWrite(led3_pin,0);//引脚输出低电平
  digitalWrite(led4_pin,0);//引脚输出低电平
}

void loop() {
  g_key=key_scan(0);  //检测按键
  if(g_key==KEY1_PRESS)//KEY1按下，D1指示灯状态翻转
  {
    g_led1_sta=!g_led1_sta; 
    digitalWrite(led1_pin,g_led1_sta);
  }
  else if(g_key==KEY2_PRESS)//KEY2按下，D2指示灯状态翻转
  {
    g_led2_sta=!g_led2_sta;
    digitalWrite(led2_pin,g_led2_sta);
  }
  else if(g_key==KEY3_PRESS)//KEY3按下，D3指示灯状态翻转
  {
    g_led3_sta=!g_led3_sta;
    digitalWrite(led3_pin,g_led3_sta);
  }
  else if(g_key==KEY4_PRESS)//KEY4按下，D4指示灯状态翻转
  {
    g_led4_sta=!g_led4_sta;
    digitalWrite(led4_pin,g_led4_sta);
  }
}
