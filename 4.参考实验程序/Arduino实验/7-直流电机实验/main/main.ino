/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：直流电机实验
 * 
 * 接线说明：电机模块-->ESP32 IO
 *         (IN1)-->(15)
 *         
 *         电机模块输出-->直流电机
 *         (5V)-->任意一脚
 *         (O1)-->任意一脚
 * 
 * 实验现象：程序下载成功后，直流电机旋转3S后停止
 * 
 * 注意事项：
 * 
 */

//定义电机控制管脚
#define motor_pin   15

//类型重定义
typedef unsigned char u8;
typedef unsigned int u16;

//定义全局变量

void setup() {
  pinMode(motor_pin, OUTPUT);//设置引脚为输出模式
  digitalWrite(motor_pin,1);//输出高电平，电机开启
  delay(3000);//延时3S
  digitalWrite(motor_pin,0);//输出低电平，电机停止
}

void loop() {
  
}
