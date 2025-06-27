# agv-uwb-iot

Sistema de localização em tempo real (RTLS) para um veículo autônomo guiado (AGV) seguidor de linha. 
O sistema integra tecnologias de comunicação UWB, Wi-Fi e BLE, utilizando os protocolos MQTT e CoAP. 
O AGV, controlado por um Arduino NodeMCU com ESP8266, recebe comandos de navegação via interface web utilizando CoAP
e fornece atualizações de localização em tempo real por meio da tecnologia UWB. Ao atingir o destino, o
AGV envia uma notificação via WhatsApp. A arquitetura proposta é de baixo custo, escalável e adequada
para ambientes de fábrica inteligente. Os resultados experimentais demonstram a precisão e confiabilidade
do sistema em cenários de localização indoor.

![agv](https://github.com/user-attachments/assets/1e94bc1c-8c19-4b56-bb01-86402ba699ed)
