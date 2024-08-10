/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：点亮第一个LED实验
 * 
 * 接线说明：LED模块-->ESP32 IO
 *         D1-->15
 * 
 * 实验现象：程序下载成功后，D1指示灯点亮
 * 
 * 注意事项：
 * 
 */

//定义LED1管脚
#define LED1 15

void setup() {
  //设置LED1引脚为输出模式
  pinMode(LED1, OUTPUT);
  //LED1引脚输出高电平，点亮
  digitalWrite(LED1, HIGH);
}

void loop() {
  
}
