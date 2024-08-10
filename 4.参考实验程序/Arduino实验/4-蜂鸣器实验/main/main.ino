/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：蜂鸣器实验
 * 
 * 接线说明：蜂鸣器模块-->ESP32 IO
 *         (BEEP)-->(25)
 * 
 * 实验现象：程序下载成功后，BEEP模块发出声音
 * 
 * 注意事项：
 * 
 */

//定义蜂鸣器控制管脚
#define beep_pin  25
char g_i=0;

void setup() {
  pinMode(beep_pin, OUTPUT);//设置引脚为输出模式
}

void loop() {
  g_i=!g_i;
  digitalWrite(beep_pin,g_i);//引脚输出电平翻转
  delayMicroseconds(250);//延时250us
}
