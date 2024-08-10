/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：继电器实验
 * 
 * 接线说明：继电器模块-->ESP32 IO
 *         (REL)-->(25)
 *         
 *         继电器模块输出-->LED模块
 *         (COM)-->(3V3)
           (NO)-->(D1)
 * 
 * 实验现象：程序下载成功后，继电器模块间隔一定时间吸合断开，吸合时D1指示灯亮，断开时灭
 * 
 * 注意事项：
 * 
 */

//定义继电器控制管脚
#define relay_pin   25
char g_i=0;

void setup() {
  pinMode(relay_pin, OUTPUT);//设置引脚为输出模式
}

void loop() {
  g_i=!g_i;
  digitalWrite(relay_pin,g_i);//引脚输出电平翻转
  delay(1000);//延时1000ms
}
