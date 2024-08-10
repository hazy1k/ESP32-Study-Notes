#ifndef _dht11_H
#define _dht11_H

#include "public.h"

//DHT11管脚定义
#define dht11_pin   27

#define DHT11_DQ_LOW    digitalWrite(dht11_pin, LOW)
#define DHT11_DQ_HIGH   digitalWrite(dht11_pin, HIGH)
#define DHT11_READ      digitalRead(dht11_pin)

#define DHT11_MODE_IN   pinMode(dht11_pin, INPUT_PULLUP)
#define DHT11_MODE_OUT  pinMode(dht11_pin, OUTPUT)


//函数声明
void DHT11_IO_OUT(void);
void DHT11_IO_IN(void);
u8 DHT11_Init(void);
void DHT11_Rst(void);
u8 DHT11_Check(void);
u8 DHT11_Read_Bit(void);
u8 DHT11_Read_Byte(void);
u8 DHT11_Read_Data(u8 *temp,u8 *humi);

#endif
