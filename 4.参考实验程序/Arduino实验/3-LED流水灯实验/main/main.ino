/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：LED流水灯实验
 * 
 * 接线说明：LED模块-->ESP32 IO
 *         (D1-D8)-->(15,2,0,4,16,17,5,18)
 * 
 * 实验现象：程序下载成功后，LED模块D1-D8指示灯依次点亮后依次熄灭
 * 
 * 注意事项：
 * 
 */

//定义LED管脚
const char led_pin[8]={15,2,0,4,16,17,5,18};
char g_i=0;

void setup() {
  char i=0;
  
  for(i=0;i<8;i++)
  {
      pinMode(led_pin[i], OUTPUT);//设置LED引脚为输出模式 
      digitalWrite(led_pin[i], LOW);//LED1引脚输出低电平，熄灭
  }
}

void loop() {
  for(g_i=0;g_i<8;g_i++)
  {
      digitalWrite(led_pin[g_i], HIGH);//LED引脚输出高电平，点亮
      delay(100);//延时100ms
  }
  for(g_i=0;g_i<8;g_i++)
  {
      digitalWrite(led_pin[g_i], LOW);//LED引脚输出低电平，熄灭
      delay(100);//延时100ms
  }

}
