#!/bin/bash

# Iniciar mqtt_to_coap.py em segundo plano e redirecionar a saída para mqtt_to_coap.log
nohup python3 mqtt_to_coap.py > mqtt_to_coap.log 2>&1 &

# Iniciar gateway_web.py em segundo plano e redirecionar a saída para gateway_web.log
nohup python3 gateway_web.py > gateway_web.log 2>&1 &

# Exibir mensagem de sucesso
echo "Os programas mqtt_to_coap.py e gateway_web.py foram iniciados em segundo plano."
