import os
import asyncio
import json
import time
import paho.mqtt.client as mqtt
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from aiocoap import *
from twilio.rest import Client

# CONFIGURAÇÕES
MQTT_BROKER = "192.168.241.7"
MQTT_TOPIC = "dwm/node/4685/uplink/location"
NODEMCU_IP = "192.168.241.40"
DESTINO = {"x": 1.6, "y": 3.0}
ORIGEM = {"x": 0.0, "y": 0.0}
TOLERANCIA = 0.3

# Dados da conta Twilio
TWILIO_SID = "ACe658214e9c9563081a7a75a6e84d50ed"
TWILIO_TOKEN = "b5bc525b264ae1f0aed120c625323955"
TWILIO_WHATSAPP_FROM = "+14155238886"
TWILIO_WHATSAPP_TO = "+554799114215"

# content_sid específicos
CONTENT_SID_DESTINO = "HX7a6a7c6caa0b6cf34e43b5fdfab28981"
CONTENT_SID_ORIGEM = "HXd0b701f95b1f4080a8854d1582c91447"

# Estado compartilhado
estado = {
    "ja_enviou_stop": False,
    "posicao_atual": None,
    "em_viagem": False,
    "tempo_inicio": None,
    "tempo_retorno": None,
    "mensagem_enviada_destino": False,
    "mensagem_enviada_origem": False
}

# Fila para comandos CoAP
comando_queue = asyncio.Queue()

def chegou_ao_destino(pos):
    return abs(pos["x"] - DESTINO["x"]) < TOLERANCIA and abs(pos["y"] - DESTINO["y"]) < TOLERANCIA

def chegou_a_origem(pos):
    return abs(pos["x"] - ORIGEM["x"]) < TOLERANCIA and abs(pos["y"] - ORIGEM["y"]) < TOLERANCIA

async def enviar_comando_coap():
    while True:
        comando = await comando_queue.get()
        print(f"[CoAP] Comando recebido na fila: {comando}")
        if comando == "STOP":
            try:
                protocol = await Context.create_client_context()
                request = Message(code=PUT, uri=f"coap://{NODEMCU_IP}/stop", payload=b"1")
                print(f"[CoAP] Enviando comando para {NODEMCU_IP}/stop")
                response = await asyncio.wait_for(protocol.request(request).response, timeout=5)
                print("[CoAP] Resposta do NodeMCU:", response.payload.decode())
            except asyncio.TimeoutError:
                print("[CoAP] Timeout ao tentar enviar comando STOP.")
            except Exception as e:
                print("[CoAP] Erro ao enviar comando:", e)

def enviar_whatsapp(mensagem, content_sid):
    print(f"[Twilio] Preparando envio: {mensagem}")
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            from_=f'whatsapp:{TWILIO_WHATSAPP_FROM}',
            to=f'whatsapp:{TWILIO_WHATSAPP_TO}',
            content_sid=content_sid,
        )
        print(f"[Twilio] Mensagem enviada com sucesso. SID: {message.sid}")
    except Exception as e:
        print(f"[Twilio] Erro ao enviar WhatsApp: {e}")
        raise

async def enviar_whatsapp_async(mensagem, content_sid):
    print("[Twilio] Iniciando envio de mensagem WhatsApp...")
    try:
        await asyncio.to_thread(enviar_whatsapp, mensagem, content_sid)
        print("[Twilio] Envio de mensagem WhatsApp concluído.")
    except Exception as e:
        print(f"[Twilio] Falha ao enviar mensagem WhatsApp: {e}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        x = float(payload["position"]["x"])
        y = float(payload["position"]["y"])
        if not (x == x and y == y):  # Verifica se é NaN
            return
        pos = {"x": x, "y": y}
        estado["posicao_atual"] = pos
    except Exception as e:
        print("[MQTT] Erro ao processar mensagem:", e)

async def monitorar_posicao():
    while True:
        await asyncio.sleep(0.5)
        pos = estado["posicao_atual"]
        if pos:
            if chegou_ao_destino(pos):
                if not estado.get("mensagem_enviada_destino", False):
                    estado["em_viagem"] = True
                    estado["tempo_inicio"] = time.time()
                    estado["mensagem_enviada_destino"] = True

                    print("[Monitoramento] Chegou ao destino.")
                    await comando_queue.put("STOP")

                    mensagem = "O seguidor chegou ao destino. Comando STOP enviado."
                    asyncio.create_task(enviar_whatsapp_async(mensagem, CONTENT_SID_DESTINO))

            elif chegou_a_origem(pos) and estado["em_viagem"]:
                if not estado.get("mensagem_enviada_origem", False):
                    estado["tempo_retorno"] = time.time()
                    estado["mensagem_enviada_origem"] = True

                    print("[Monitoramento] Retornou à origem.")
                    await comando_queue.put("STOP")

                    tempo_total = estado["tempo_retorno"] - estado["tempo_inicio"]
                    mensagem = f"O seguidor retornou à origem. Tempo total: {tempo_total:.2f} segundos. Comando STOP enviado."
                    asyncio.create_task(enviar_whatsapp_async(mensagem, CONTENT_SID_ORIGEM))

def main():
    #client = mqtt.Client(protocol=mqtt.MQTTv5)
    client = mqtt.Client()

    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(enviar_comando_coap())
    loop.create_task(monitorar_posicao())
    loop.run_forever()

if __name__ == "__main__":
    os.system('clear')
    print("[Sistema] Aguardando dados de localização da tag...")
    main()
