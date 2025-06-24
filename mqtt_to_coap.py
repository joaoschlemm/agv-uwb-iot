
import asyncio
import json
import paho.mqtt.client as mqtt
from aiocoap import *
from twilio.rest import Client

# CONFIGURAÇÕES
MQTT_BROKER = "192.168.190.7"
MQTT_TOPIC = "dwm/node/4685/uplink/location"
NODEMCU_IP = "192.168.190.40"
DESTINO = {"x": 1.6, "y": 3.0}
TOLERANCIA = 0.3

# Dados da conta Twilio
TWILIO_SID = "***"
TWILIO_TOKEN = "***"
TWILIO_WHATSAPP_FROM = "+***"
TWILIO_WHATSAPP_TO = "+55***"

# Estado compartilhado
estado = {
    "ja_enviou_stop": False,
    "posicao_atual": None
}

# Fila para comandos CoAP
comando_queue = asyncio.Queue()

def chegou_ao_destino(pos):
    return abs(pos["x"] - DESTINO["x"]) < TOLERANCIA and abs(pos["y"] - DESTINO["y"]) < TOLERANCIA

async def enviar_comando_coap():
    while True:
        comando = await comando_queue.get()
        print(f"[CoAP] Comando recebido na fila: {comando}")
        if comando == "STOP":
            sucesso = False
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
            else:
                sucesso = True

            # Envia WhatsApp independentemente do sucesso do CoAP
            mensagem = "O seguidor chegou ao destino. "
            mensagem += "Comando STOP enviado com sucesso." if sucesso else "Falha ao enviar comando STOP."
            asyncio.create_task(enviar_whatsapp_async(mensagem))

def enviar_whatsapp(mensagem):
    print(f"[Twilio] Preparando envio: {mensagem}")
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
#            body=mensagem,
            from_=f'whatsapp:{TWILIO_WHATSAPP_FROM}',
            to=f'whatsapp:{TWILIO_WHATSAPP_TO}',
            content_sid="HXfc92efcb2636b564eb7d4163960bad11",
        )
        print(f"[Twilio] Mensagem enviada com sucesso. SID: {message.sid}")
    except Exception as e:
        print(f"[Twilio] Erro ao enviar WhatsApp: {e}")
        raise

async def enviar_whatsapp_async(mensagem):
    print("[Twilio] Iniciando envio de mensagem WhatsApp...")
    try:
        await asyncio.to_thread(enviar_whatsapp, mensagem)
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
#        print(f"[MQTT] Posição atual recebida: {pos}")
    except Exception as e:
        print("[MQTT] Erro ao processar mensagem:", e)

async def monitorar_posicao():
    while True:
        await asyncio.sleep(0.5)
        pos = estado["posicao_atual"]
        if pos:
            if chegou_ao_destino(pos):
                print("[Monitoramento] Dentro da área de tolerância.")
                print(f"[MQTT] Posição atual recebida: {pos}")
                if not estado["ja_enviou_stop"]:
                    print("[Monitoramento] Chegou ao destino! Enviando comando STOP via CoAP...")
                    print(f"[MQTT] Posição atual recebida: {pos}")
                    await comando_queue.put("STOP")
                    estado["ja_enviou_stop"] = True
            else:
                print("[Monitoramento] Fora da área de tolerância.")
                print(f"[MQTT] Posição atual recebida: {pos}")
                # Não reseta a flag para evitar reenvio desnecessário

def main():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()

    loop = asyncio.get_event_loop()
    loop.create_task(enviar_comando_coap())
    loop.create_task(monitorar_posicao())
    loop.run_forever()

if __name__ == "__main__":
    print("[Sistema] Aguardando dados de localização da tag...")
    main()
