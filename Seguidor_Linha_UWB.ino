
/*
     AUTOR:     Joao Schlemm
     SKETCH:    Seguidor de Linha AGV
     DATA:      23/06/2025
*/

// DEFINIÇÕES DE PINOS PARA NodeMCU
#define pinSensorDir D2  
#define pinSensorEsq D1  

#define dirFrente D5     
#define dirTras   D6     
#define esqFrente D7     
#define esqTras   D8     

// DEFINIÇÕES
#define LINHA HIGH  

#define FRENTE  1
#define PARADO  0
#define TRAS   -1

// Definição WiFi
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <coap-simple.h>
#include <ESP8266WebServer.h>

// DECLARAÇÃO DE FUNÇÕES
void configMotor();
void motorEsq(int direcao, byte velocidade = 85);
void motorDir(int direcao, byte velocidade = 85);
void iniciarPercurso();
void pararPercurso();
void inverterLogica();
void executarPercurso();
void callback(CoapPacket &packet, IPAddress ip, int port);
void handleRoot();
void handleStart();
void handleStop();
void handleInverterLogica();
void handleStatus();
void handleSetVelocidade();
void handleMover();

// DECLARAÇÃO DE VARIÁVEIS
bool leituraEsquerda;
bool leituraDireita;
bool percursoAtivo = false;
int logicaLinha = LINHA;
int velEsq = 100;
int velDir = 100;

const char* ssid = "***";
const char* password = "***";

WiFiUDP udp;
Coap coap(udp);
ESP8266WebServer server(80);

void setup() {
  pinMode(pinSensorDir, INPUT);
  pinMode(pinSensorEsq, INPUT);

  configMotor();

  Serial.begin(9600);
  delay(10);

  // Configuração WiFi
  Serial.println();
  Serial.print("Conectando-se a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi conectado com sucesso!");
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());

  // Configuração CoAP
  coap.server(callback, "start");
  coap.server([](CoapPacket &packet, IPAddress ip, int port) {
    pararPercurso();
    coap.sendResponse(ip, port, packet.messageid, "Percurso parado");
  }, "stop");
  coap.server([](CoapPacket &packet, IPAddress ip, int port) {
    inverterLogica();
    coap.sendResponse(ip, port, packet.messageid, "Lógica invertida");
  }, "inverterLogica");
  coap.server([](CoapPacket &packet, IPAddress ip, int port) {
    String status = "{";
    status += "\"sensorEsquerdo\": " + String(digitalRead(pinSensorEsq)) + ",";
    status += "\"sensorDireito\": " + String(digitalRead(pinSensorDir)) + ",";
    status += "\"percurso\": \"" + String(percursoAtivo ? "START" : "STOP") + "\",";
    status += "\"logica\": \"" + String(logicaLinha == LOW ? "LOW" : "HIGH") + "\"";
    status += "}";
    coap.sendResponse(ip, port, packet.messageid, status.c_str());
  }, "status");
  coap.start();

  // Configuração Web Server
  server.on("/", handleRoot);
  server.on("/start", handleStart);
  server.on("/stop", handleStop);
  server.on("/inverterLogica", handleInverterLogica);
  server.on("/status", handleStatus);
  server.on("/setVelocidade", handleSetVelocidade);
  server.on("/mover", handleMover);
  server.begin();
  Serial.println("Servidor HTTP iniciado!");
}

void loop() {
  coap.loop();
  server.handleClient();

  if (percursoAtivo) {
    executarPercurso();
  } else {
    // Garante que os motores parem quando percursoAtivo for false
    motorEsq(PARADO);
    motorDir(PARADO);
  }

  yield(); // Evita WDT reset
}

// IMPLEMENTO DE FUNÇÕES

void configMotor() {
  pinMode(dirFrente,  OUTPUT);
  pinMode(dirTras,    OUTPUT);
  pinMode(esqFrente,  OUTPUT);
  pinMode(esqTras,    OUTPUT);

  digitalWrite(dirFrente,  LOW);
  digitalWrite(dirTras,    LOW);
  digitalWrite(esqFrente,  LOW);
  digitalWrite(esqTras,    LOW);
}

void motorEsq(int direcao, byte velocidade) {
  switch (direcao) {
    case -1:
      //Serial.println("Esq Trás");
      digitalWrite(esqFrente,  LOW);
      analogWrite (esqTras,    velocidade);
      break;
    case 0:
      //Serial.println("Esq PARADO");
      digitalWrite(esqFrente,  HIGH);
      digitalWrite(esqTras,    HIGH);
      break;
    case 1:
      //Serial.println("Esq Frente");
      analogWrite (esqFrente,  velocidade);
      digitalWrite(esqTras,    LOW);
      break;
  }
}

void motorDir(int direcao, byte velocidade) {
  switch (direcao) {
    case -1:
      //Serial.println("Dir Trás");
      digitalWrite(dirFrente,  LOW);
      analogWrite (dirTras,    velocidade);
      break;
    case 0:
      //Serial.println("Dir PARADO");
      digitalWrite(dirFrente,  HIGH);
      digitalWrite(dirTras,    HIGH);
      break;
    case 1:
      //Serial.println("Dir Frente");
      analogWrite (dirFrente,  velocidade);
      digitalWrite(dirTras,    LOW);
      break;
  }
}

void iniciarPercurso() {
  Serial.println("Percurso iniciado!");
  percursoAtivo = true;
}

void pararPercurso() {
  Serial.println("Percurso parado!");
  percursoAtivo = false;
}

void inverterLogica() {
  logicaLinha = (logicaLinha == LOW) ? HIGH : LOW;
  Serial.println("Lógica de detecção invertida!");
}

void executarPercurso() {
  bool valE = digitalRead(pinSensorEsq);
  bool valD = digitalRead(pinSensorDir);

  if (valE == logicaLinha && valD == logicaLinha) {
    motorEsq(PARADO);
    motorDir(PARADO);
    delay(300);
    motorEsq(TRAS);
    motorDir(TRAS);
    delay(150);
    motorEsq(PARADO);
    motorDir(PARADO);
    delay(3000);
  } else if (valD == logicaLinha) {
    motorEsq(FRENTE, 100);
    motorDir(TRAS, 100);
  } else if (valE == logicaLinha) {
    motorEsq(TRAS, 100);
    motorDir(FRENTE, 100);
  } else {
    motorEsq(FRENTE);
    motorDir(FRENTE);
  }
}

void callback(CoapPacket &packet, IPAddress ip, int port) {
  iniciarPercurso();
  coap.sendResponse(ip, port, packet.messageid, "Percurso iniciado");
}

// Funções do servidor web

void handleRoot() {
  String html = R"rawliteral(
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="UTF-8">
    <title>Seguidor de Linha v1.0</title>
    <style>
      body { font-family: Arial; text-align: center; margin: 20px; }
      button { margin: 5px; padding: 10px 20px; font-size: 16px; }
      input[type=range] { width: 200px; }
    </style>
  </head>
  <body>
    <h1>Seguidor de Linha v1.0</h1>

    <h3>Status dos Sensores</h3>
    <p>Sensor Esquerdo: <span id="sensorEsq">--</span></p>
    <p>Sensor Direito: <span id="sensorDir">--</span></p>
    <p>Status do Percurso: <span id="statusPercurso">--</span></p>
    <p>Lógica de Detecção: <span id="logica">--</span></p>

    <h3>Controle de Velocidade</h3>
    <p>Esquerda: <input type="range" min="0" max="255" value="75" id="velEsq" onchange="atualizarVelocidade()"></p>
    <p>Direita: <input type="range" min="0" max="255" value="75" id="velDir" onchange="atualizarVelocidade()"></p>

    <h3>Controle Remoto</h3>
    <button onclick="enviarComando('/start')">Start</button>
    <button onclick="enviarComando('/stop')">Stop</button>
    <button onclick="enviarComando('/inverterLogica')">Inverter Lógica</button>
    <br>

    <script>
      function atualizarStatus() {
        fetch('/status')
          .then(res => res.json())
          .then(data => {
            document.getElementById('sensorEsq').textContent = data.sensorEsquerdo;
            document.getElementById('sensorDir').textContent = data.sensorDireito;
            document.getElementById('statusPercurso').textContent = data.percurso;
            document.getElementById('logica').textContent = data.logica;
          });
      }

      function atualizarVelocidade() {
        let esq = document.getElementById('velEsq').value;
        let dir = document.getElementById('velDir').value;
        fetch(`/setVelocidade?esq=${esq}&dir=${dir}`);
      }

      function enviarComando(endpoint) {
        fetch(endpoint);
      }

      function mover(direcao) {
        fetch(`/mover?dir=${direcao}`);
      }

      setInterval(atualizarStatus, 1000);
    </script>
  </body>
  </html>
  )rawliteral";

  server.send(200, "text/html", html);
}

void handleStart() {
  iniciarPercurso();
  server.send(200, "text/html", "<html><head><meta charset=\"UTF-8\"></head><body><h1>Comando Start enviado!</h1></body></html>");
}

void handleStop() {
  pararPercurso();
  server.send(200, "text/html", "<html><head><meta charset=\"UTF-8\"></head><body><h1>Comando Stop enviado!</h1></body></html>");
}

void handleInverterLogica() {
  inverterLogica();
  server.send(200, "text/html", "<html><head><meta charset=\"UTF-8\"></head><body><h1>Lógica de detecção invertida!</h1></body></html>");
}

void handleStatus() {
  String status = "{";
  status += "\"sensorEsquerdo\": " + String(digitalRead(pinSensorEsq)) + ",";
  status += "\"sensorDireito\": " + String(digitalRead(pinSensorDir)) + ",";
  status += "\"percurso\": \"" + String(percursoAtivo ? "START" : "STOP") + "\",";
  status += "\"logica\": \"" + String(logicaLinha == LOW ? "LOW" : "HIGH") + "\"";
  status += "}";
  server.send(200, "application/json", status);
}

void handleSetVelocidade() {
  if (server.hasArg("esq")) velEsq = server.arg("esq").toInt();
  if (server.hasArg("dir")) velDir = server.arg("dir").toInt();
  server.send(200, "text/plain", "Velocidade atualizada");
}

void handleMover() {
  String dir = server.arg("dir");
  if (dir == "frente") {
    motorEsq(FRENTE, velEsq);
    motorDir(FRENTE, velDir);
  } else if (dir == "tras") {
    motorEsq(TRAS, velEsq);
    motorDir(TRAS, velDir);
  } else if (dir == "esq") {
    motorEsq(TRAS, velEsq);
    motorDir(FRENTE, velDir);
  } else if (dir == "dir") {
    motorEsq(FRENTE, velEsq);
    motorDir(TRAS, velDir);
  }
  server.send(200, "text/plain", "Movimento executado");
}
