/* 深圳市普中科技有限公司（PRECHIN 普中）
   技术支持：www.prechin.net
 * 
 * 实验名称：WIFI实验--Client
 * 
 * 接线说明：
 * 
 * 实验现象：程序下载成功后，手机连接的WIFI需和ESP32连接的WIFI处于同一频段（比如192.168.1.xx），
            然后在手机网页输入串口控制台输出的本机IP地址即可进入手机端网页控制板子LED。
 * 
 * 注意事项：
 */

#include "public.h"
#include <WiFiMulti.h>

WiFiMulti WiFiMulti;

const char* ssid     = "puzhong88";
const char* password = "PUZHONG88";


//WIFI连接路由器
void wifi_connect(void)
{
  Serial.print("Connecting to ");
  delay(10);

  // We start by connecting to a WiFi network
  WiFiMulti.addAP(ssid, password);

  Serial.println();
  Serial.println();
  Serial.print("Waiting for WiFi... ");

  while(WiFiMulti.run() != WL_CONNECTED) {
      Serial.print(".");
      delay(500);
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  delay(500);
}

void setup(){
  Serial.begin(115200);
  wifi_connect();
  
}
  
void loop(){
  const uint16_t port = 1337;
  const char * host = "192.168.1.17"; // ip or dns

  Serial.print("Connecting to ");
  Serial.println(host);

  // Use WiFiClient class to create TCP connections
  WiFiClient client;

  if (!client.connect(host, port)) {
      Serial.println("Connection failed.");
      Serial.println("Waiting 5 seconds before retrying...");
      delay(5000);
      return;
  }

  // This will send a request to the server
  //uncomment this line to send an arbitrary string to the server
  //client.print("Send this data to the server");
  //uncomment this line to send a basic document request to the server
  client.print("GET /index.html HTTP/1.1\n\n");

  int maxloops = 0;
  
  //wait for the server's reply to become available
  while (!client.available() && maxloops < 1000)
  {
    maxloops++;
    delay(1); //delay 1 msec
  }
  if (client.available() > 0)
  {
    //read back one line from the server
    String line = client.readStringUntil('\r');
    Serial.println(line);
  }
  else
  {
    Serial.println("client.available() timed out ");
  }

  Serial.println("Closing connection.");
  client.stop();

  Serial.println("Waiting 5 seconds before restarting...");
  delay(5000);
}

