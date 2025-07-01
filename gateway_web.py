from flask import Flask, render_template, redirect, url_for, jsonify, request
from twilio.twiml.messaging_response import MessagingResponse

import asyncio
import json
import os
from aiocoap import *

app = Flask(__name__)

ESP_IP = "coap://192.168.241.40"  # IP do NodeMCU

# Envia comando CoAP
async def enviar_comando(endpoint, payload):
    try:
        protocol = await Context.create_client_context()
        request = Message(code=PUT, uri=f"{ESP_IP}/{endpoint}", payload=payload.encode('utf-8'))
        response = await protocol.request(request).response
        return response.payload.decode()
    except Exception as e:
        print(f"[CoAP] Erro ao enviar comando para {endpoint}: {e}")
        return f"Erro: {e}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start')
def start():
    asyncio.run(enviar_comando("start", "1"))
    return redirect(url_for('index'))

@app.route('/stop')
def stop():
    asyncio.run(enviar_comando("stop", "1"))
    return redirect(url_for('index'))

@app.route('/inverter')
def inverter():
    asyncio.run(enviar_comando("inverterLogica", "1"))
    return redirect(url_for('index'))

@app.route('/setVelocidade')
def set_velocidade():
    esq = request.args.get('esq')
    dir = request.args.get('dir')
    asyncio.run(enviar_comando("setVelocidade", f"{esq},{dir}"))
    return ('', 204)

@app.route('/status')
def status():
    async def obter_status():
        try:
            protocol = await Context.create_client_context()
            request = Message(code=GET, uri=f"{ESP_IP}/status")
            response = await protocol.request(request).response
            return json.loads(response.payload.decode())
        except Exception as e:
            return {"error": str(e)}

    result = asyncio.run(obter_status())
    return jsonify(result)

@app.route('/whatsapp', methods=['GET', 'POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip().lower()
    response = MessagingResponse()
    msg = response.message()

    try:
        if incoming_msg in ['start', 'confirma']:
            asyncio.run(enviar_comando("start", "1"))
            msg.body("Robô iniciado. ✅")
        elif incoming_msg in ['stop', 'parar']:
            asyncio.run(enviar_comando("stop", "1"))
            msg.body("Robô parado. 🛑")
        elif incoming_msg == 'inverter':
            asyncio.run(enviar_comando("inverterLogica", "1"))
            msg.body("Lógica invertida. 🔄")
        elif incoming_msg.startswith('vel'):
            partes = incoming_msg.split()
            esq = int(partes[1])
            dir = int(partes[2])
            asyncio.run(enviar_comando("setVelocidade", f"{esq},{dir}"))
            msg.body(f"Velocidade atualizada: Esquerda={esq}, Direita={dir} ⚙️")
        elif incoming_msg == 'status':
            status_raw = asyncio.run(enviar_comando("status", ""))
            msg.body(f"Status atual: {status_raw}")
        else:
            msg.body("Comando não reconhecido. Envie:\n- start\n- stop\n- inverter\n- vel 100 120\n- status")
    except Exception as e:
        msg.body(f"Ocorreu um erro: {e}")

    return str(response)

if __name__ == '__main__':
    os.system('clear')
    app.run(host='0.0.0.0', port=8088)
