/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：RGB彩灯实验
 * 
 * 接线说明：RGB彩灯模块-->ESP32 IO
 *         WS-->(16)
 * 
 * 实验现象：程序下载成功后，RGB彩灯循环点亮且循环变化颜色
 * 
 * 注意事项：需要在软件中选择"项目"-->"加载库"-->"管理库"-->输入"Adafruit_NeoPixel"安装即可。
 * 
 */

#include "public.h"
#include <Adafruit_NeoPixel.h>

// 设置灯珠数量
#define NUMPIXELS        5

// 设置输出数据引脚
#define PIN_NEOPIXEL    16

// 初始化灯珠控制实例
Adafruit_NeoPixel pixels(NUMPIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// 当前灯珠指向
int16_t idx = 0;


// 启动设置
void setup() {
  // 调试串口速率设置
  Serial.begin(115200);

  // 灯珠控制开始
  pixels.begin();

  // 设置亮度为255
  pixels.setBrightness(255);

  // 设置灯珠颜色，全部关闭
  pixels.fill(0x000000);

  delay(100);

  // 设置灯珠颜色
  pixels.fill(0xFF0000);

  delay(100);

  pixels.clear();
}


uint16_t c1 = 0;
uint16_t c2 = 0;
uint16_t c3 = 0;     
uint16_t sign_bit =0;
uint16_t sign = 1;
// 循环主体程序
void loop() {
    if(sign_bit == 0)
    {
      //这个if语句在循环体内只运行一次，该if语句及下方if语句可以用switch代替
        if(sign)
        {
          c1++;
          if(c1>=255)
            sign=0;
        }
        else
        {
          c2++;
          if(c2>=255)
          {
            sign=1;
            sign_bit = 1;
          }
        }
    }
    if(sign_bit == 1)
    {
        if(sign)
        {
          c1--;
          if(c1<=0)
            sign=0;
        }
        else
        {
          c3++;
          if(c3>=255)
          {
            sign=1;
            sign_bit = 2;
          }
        }
    }
    if(sign_bit == 2)
    {
        if(sign)
        {
          c2--;
          if(c2<=0)
            sign=0;
        }
        else
        {
          c1++;
          if(c1>=255)
          {
            sign=1;
            sign_bit = 3;
          }
        }
    }
    if(sign_bit == 3)
    {
        if(sign)
        {
          c3--;
          if(c3<=0)
            sign=0;
        }
        else
        {
          c2++;
          if(c2>=255)
          {
            sign=1;
            sign_bit = 1;
          }
        }
    }
  
    //在这里注释的是一个一个将灯珠点亮并实现渐变
    idx++;
    if(idx > 5)
    {
      idx = 0;
    }
    pixels.setPixelColor(idx, pixels.Color(c1,c2,c3));

    
    /*=======================================
    全部点亮用该函数
    pixels.fill(pixels.Color(c1,c2,c3));
    =======================================*/
  
    delay(10);//延时，改变速度
    // 显示
    pixels.show();
  
}
