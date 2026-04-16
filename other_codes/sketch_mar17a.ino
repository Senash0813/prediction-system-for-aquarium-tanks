#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <BH1750.h>
#include <time.h>

// ========================================================
// SECRETS / CONFIG
// ========================================================
const char* ssid = "Dialog 4G 053";
const char* password = "C271F9f3";

// Backend REST API
const char* backendUrl = "http://aqua-gaurd-esp32.onrender.com/api/sensor-data";

// ThingsBoard MQTT
const char* tbServer = "thingsboard.cloud";
const int tbPort = 1883;
const char* tbToken = "ahMyRmwdcMTZtdoQiEul";

// Telegram
String telegramBotToken = "8406793777:AAHbbbIQ3pftVcfRya710FaRt8cEl8F95B0";
String telegramChatId   = "8331451609";


// ========================================================
// TIME SETTINGS
// Sri Lanka UTC+5:30
// ========================================================
const long gmtOffset_sec = 19800;
const int daylightOffset_sec = 0;

// ========================================================
// SEND INTERVAL
// ========================================================
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 180000; // 3 min

// Optional Telegram cooldown
unsigned long lastTelegramAlertTime = 0;
const unsigned long telegramAlertGap = 30000; // 30 sec, set 0 to disable cooldown

// ========================================================
// THRESHOLDS
// ========================================================
const float TEMP_THRESHOLD_HIGH        = 45.0;
const float LIGHT_THRESHOLD_HIGH       = 2000.0;
const float PH_THRESHOLD_LOW           = 2.5;
const float PH_THRESHOLD_HIGH          = 8.5;
const float TDS_THRESHOLD_HIGH         = 1000.0;
const float TURBIDITY_THRESHOLD_HIGH   = 3000.0; // NTU

// ========================================================
// ALERT LATCHES
// ========================================================
bool tempAlertSent = false;
bool lightAlertSent = false;
bool phLowAlertSent = false;
bool phHighAlertSent = false;
bool tdsAlertSent = false;
bool turbidityAlertSent = false;

// Sensor disconnect latches
bool tempSensorDisconnected = false;
bool lightSensorDisconnected = false;
bool tdsSensorDisconnected = false;
bool turbiditySensorDisconnected = false;
bool phSensorDisconnected = false;

// ========================================================
// SENSOR PINS
// ========================================================
#define TEMP_PIN       4
#define TDS_PIN        33
#define TURBIDITY_PIN  35
#define PH_PIN         34

#define VREF                 3.3
#define ADC_RESOLUTION       4095
#define ADC_LOW_WARNING      20
#define ADC_HIGH_WARNING     4075

#define TDS_SAMPLES          30
#define TURBIDITY_SAMPLES    50
#define PH_SAMPLES           20

// pH calibration values
float PH7_VOLTAGE = 2.50;
float PH4_VOLTAGE = 3.00;

// Turbidity calibration values
const float TURBIDITY_CLEAR_VOLTAGE = 2.70;
const float TURBIDITY_DIRTY_VOLTAGE = 1.20;
const float MAX_NTU = 1000.0;

// ========================================================
// OBJECTS
// ========================================================
OneWire oneWire(TEMP_PIN);
DallasTemperature tempSensor(&oneWire);
BH1750 lightMeter;

WiFiClient espClient;
PubSubClient tbClient(espClient);

bool bh1750Initialized = false;

// ========================================================
// DATA STRUCT
// ========================================================
struct SensorData {
  float temperature;
  float tds;
  float turbidityNTU;
  float light;
  float ph;
  String timestamp;

  bool tempValid;
  bool tdsValid;
  bool turbidityValid;
  bool lightValid;
  bool phValid;

  float rawTDS;
  float rawTurbidity;
  float rawPH;
};

// ========================================================
// WIFI
// ========================================================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connection failed");
  }
}

// ========================================================
// NTP TIME
// ========================================================
void setupTime() {
  configTime(gmtOffset_sec, daylightOffset_sec, "pool.ntp.org", "time.nist.gov");

  Serial.print("Syncing time");
  time_t now = time(nullptr);

  int attempts = 0;
  while (now < 100000 && attempts < 40) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
    attempts++;
  }

  Serial.println();

  if (now >= 100000) {
    Serial.println("Time synced successfully");
  } else {
    Serial.println("Time sync failed");
  }
}

String getTimestamp() {
  time_t now = time(nullptr);

  if (now < 100000) {
    return "time_not_synced";
  }

  struct tm timeinfo;
  localtime_r(&now, &timeinfo);

  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &timeinfo);

  return String(buffer);
}

// ========================================================
// THINGSBOARD MQTT
// ========================================================
bool connectThingsBoard() {
  if (tbClient.connected()) return true;

  tbClient.setServer(tbServer, tbPort);

  Serial.print("Connecting to ThingsBoard...");
  if (tbClient.connect("ESP32_FishTank", tbToken, NULL)) {
    Serial.println(" connected");
    return true;
  } else {
    Serial.print(" failed, rc=");
    Serial.println(tbClient.state());
    return false;
  }
}

// ========================================================
// URL ENCODE FOR TELEGRAM
// ========================================================
String urlEncode(const String &str) {
  String encoded = "";
  char c;
  char code0;
  char code1;

  for (int i = 0; i < str.length(); i++) {
    c = str.charAt(i);

    if (isalnum(c)) {
      encoded += c;
    } else if (c == ' ') {
      encoded += "%20";
    } else if (c == '\n') {
      encoded += "%0A";
    } else {
      code1 = (c & 0x0F) + '0';
      if ((c & 0x0F) > 9) code1 = (c & 0x0F) - 10 + 'A';

      c = (c >> 4) & 0x0F;
      code0 = c + '0';
      if (c > 9) code0 = c - 10 + 'A';

      encoded += '%';
      encoded += code0;
      encoded += code1;
    }
  }

  return encoded;
}

// ========================================================
// TELEGRAM SEND
// ========================================================
void sendTelegramMessage(String message) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected - Telegram send skipped");
    return;
  }

  if (telegramAlertGap > 0 && (millis() - lastTelegramAlertTime < telegramAlertGap)) {
    Serial.println("Telegram cooldown active - alert skipped");
    return;
  }

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient https;

  String encodedMessage = urlEncode(message);
  String url = "https://api.telegram.org/bot" + telegramBotToken +
               "/sendMessage?chat_id=" + telegramChatId +
               "&text=" + encodedMessage;

  Serial.println("Sending Telegram alert...");
  https.begin(client, url);
  int code = https.GET();

  Serial.print("Telegram HTTP code: ");
  Serial.println(code);

  if (code > 0) {
    Serial.println(https.getString());
    lastTelegramAlertTime = millis();
  } else {
    Serial.println("Telegram send failed");
  }

  https.end();
}

// ========================================================
// SENSOR STATUS TELEGRAM HELPERS
// ========================================================
void notifySensorDisconnected(const String &sensorName) {
  String msg = "Fish Tank Alert\n";
  msg += sensorName + " sensor disconnected\n";
  msg += "Please check wiring / power / connection";
  sendTelegramMessage(msg);
}

void notifySensorReconnected(const String &sensorName) {
  String msg = "Fish Tank Update\n";
  msg += sensorName + " sensor reconnected successfully";
  sendTelegramMessage(msg);
}

// ========================================================
// HELPERS
// ========================================================
bool isAnalogReadingInvalid(float rawADC) {
  return (rawADC <= ADC_LOW_WARNING || rawADC >= ADC_HIGH_WARNING);
}

int getMedianNum(int bArray[], int iFilterLen) {
  int bTab[TDS_SAMPLES];

  for (int i = 0; i < iFilterLen; i++) {
    bTab[i] = bArray[i];
  }

  int i, j, bTemp;
  for (j = 0; j < iFilterLen - 1; j++) {
    for (i = 0; i < iFilterLen - j - 1; i++) {
      if (bTab[i] > bTab[i + 1]) {
        bTemp = bTab[i];
        bTab[i] = bTab[i + 1];
        bTab[i + 1] = bTemp;
      }
    }
  }

  if ((iFilterLen & 1) > 0) {
    return bTab[(iFilterLen - 1) / 2];
  } else {
    return (bTab[iFilterLen / 2] + bTab[iFilterLen / 2 - 1]) / 2;
  }
}

float readAverageAnalog(int pin, int samples, int delayMs) {
  long total = 0;
  for (int i = 0; i < samples; i++) {
    total += analogRead(pin);
    delay(delayMs);
  }
  return total / (float)samples;
}

float estimateNTU(float turbidityVoltage) {
  if (turbidityVoltage >= TURBIDITY_CLEAR_VOLTAGE) return 0.0;
  if (turbidityVoltage <= TURBIDITY_DIRTY_VOLTAGE) return MAX_NTU;

  float ratio = (TURBIDITY_CLEAR_VOLTAGE - turbidityVoltage) /
                (TURBIDITY_CLEAR_VOLTAGE - TURBIDITY_DIRTY_VOLTAGE);

  float ntu = ratio * MAX_NTU;
  if (ntu < 0) ntu = 0;
  if (ntu > MAX_NTU) ntu = MAX_NTU;

  return ntu;
}

float calculatePH(float phVoltage) {
  float slope = (4.0 - 7.0) / (PH4_VOLTAGE - PH7_VOLTAGE);
  float pHValue = 7.0 + slope * (phVoltage - PH7_VOLTAGE);

  if (pHValue < 0.0) pHValue = 0.0;
  if (pHValue > 14.0) pHValue = 14.0;

  return pHValue;
}

// ========================================================
// SENSOR READS
// ========================================================
float readTemperature(bool &valid) {
  tempSensor.requestTemperatures();
  float temperature = tempSensor.getTempCByIndex(0);

  if (temperature == DEVICE_DISCONNECTED_C) {
    Serial.println("Temperature sensor error");

    if (!tempSensorDisconnected) {
      notifySensorDisconnected("Temperature");
      tempSensorDisconnected = true;
    }

    valid = false;
    return -1.0;
  }

  if (tempSensorDisconnected) {
    notifySensorReconnected("Temperature");
    tempSensorDisconnected = false;
  }

  valid = true;
  return temperature;
}

float readTDS(float temperature, float &rawADC, bool &valid) {
  int tdsBuffer[TDS_SAMPLES];

  for (int i = 0; i < TDS_SAMPLES; i++) {
    tdsBuffer[i] = analogRead(TDS_PIN);
    delay(40);
  }

  int tdsMedian = getMedianNum(tdsBuffer, TDS_SAMPLES);
  rawADC = tdsMedian;

  if (isAnalogReadingInvalid(rawADC)) {
    if (!tdsSensorDisconnected) {
      notifySensorDisconnected("TDS");
      tdsSensorDisconnected = true;
    }

    valid = false;
    return -1.0;
  }

  if (tdsSensorDisconnected) {
    notifySensorReconnected("TDS");
    tdsSensorDisconnected = false;
  }

  float tdsVoltage = tdsMedian * (VREF / 4095.0);
  float compensationCoefficient = 1.0 + 0.02 * (temperature - 25.0);
  float compensationVoltage = tdsVoltage / compensationCoefficient;

  float tdsValue = (133.42 * compensationVoltage * compensationVoltage * compensationVoltage
                  - 255.86 * compensationVoltage * compensationVoltage
                  + 857.39 * compensationVoltage) * 0.5;

  if (tdsValue < 0) tdsValue = 0;

  valid = true;
  return tdsValue;
}

float readLight(bool &valid) {
  if (!bh1750Initialized) {
    Serial.println("Light sensor not initialized");

    if (!lightSensorDisconnected) {
      notifySensorDisconnected("Light");
      lightSensorDisconnected = true;
    }

    valid = false;
    return -1.0;
  }

  float lux = lightMeter.readLightLevel();

  if (lux < 0) {
    Serial.println("Light sensor read failed");

    if (!lightSensorDisconnected) {
      notifySensorDisconnected("Light");
      lightSensorDisconnected = true;
    }

    valid = false;
    return -1.0;
  }

  if (lightSensorDisconnected) {
    notifySensorReconnected("Light");
    lightSensorDisconnected = false;
  }

  valid = true;
  return lux;
}

float readTurbidity(float &rawADC, bool &valid) {
  rawADC = readAverageAnalog(TURBIDITY_PIN, TURBIDITY_SAMPLES, 10);

  if (isAnalogReadingInvalid(rawADC)) {
    if (!turbiditySensorDisconnected) {
      notifySensorDisconnected("Turbidity");
      turbiditySensorDisconnected = true;
    }

    valid = false;
    return -1.0;
  }

  if (turbiditySensorDisconnected) {
    notifySensorReconnected("Turbidity");
    turbiditySensorDisconnected = false;
  }

  float voltage = rawADC * (VREF / 4095.0);
  float ntu = estimateNTU(voltage);

  valid = true;
  return ntu;
}

float readPH(float &rawADC, bool &valid) {
  rawADC = readAverageAnalog(PH_PIN, PH_SAMPLES, 20);

  if (isAnalogReadingInvalid(rawADC)) {
    if (!phSensorDisconnected) {
      notifySensorDisconnected("pH");
      phSensorDisconnected = true;
    }

    valid = false;
    return -1.0;
  }

  if (phSensorDisconnected) {
    notifySensorReconnected("pH");
    phSensorDisconnected = false;
  }

  float phVoltage = rawADC * (VREF / 4095.0);
  float pHValue = calculatePH(phVoltage);

  valid = true;
  return pHValue;
}

SensorData readAllSensors() {
  SensorData data;

  data.timestamp = getTimestamp();

  data.temperature = readTemperature(data.tempValid);

  float temperatureForCompensation = data.tempValid ? data.temperature : 25.0;

  data.tds = readTDS(temperatureForCompensation, data.rawTDS, data.tdsValid);
  data.light = readLight(data.lightValid);
  data.turbidityNTU = readTurbidity(data.rawTurbidity, data.turbidityValid);
  data.ph = readPH(data.rawPH, data.phValid);

  return data;
}

// ========================================================
// BACKEND SEND
// ========================================================
void sendToBackend(const SensorData &data) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected - backend send skipped");
    return;
  }

  HTTPClient http;
  http.begin(backendUrl);
  http.addHeader("Content-Type", "application/json");

  String mac = WiFi.macAddress();

  String jsonData = "{";
  jsonData += "\"mac\":\"" + mac + "\",";
  jsonData += "\"temperature\":" + String(data.temperature, 2) + ",";
  jsonData += "\"turbidity\":" + String(data.turbidityNTU, 2) + ",";
  jsonData += "\"tds\":" + String(data.tds, 2) + ",";
  jsonData += "\"light\":" + String(data.light, 2) + ",";
  jsonData += "\"ph\":" + String(data.ph, 2) + ",";
  jsonData += "\"timestamp\":\"" + data.timestamp + "\"";
  jsonData += "}";

  Serial.println("Sending to backend:");
  Serial.println(jsonData);

  int code = http.POST(jsonData);
  Serial.print("Backend HTTP code: ");
  Serial.println(code);

  if (code > 0) {
    Serial.println(http.getString());
  } else {
    Serial.println("Backend POST failed");
  }

  http.end();
}

// ========================================================
// THINGSBOARD SEND
// ========================================================
void sendToThingsBoard(const SensorData &data) {
  if (!connectThingsBoard()) {
    Serial.println("Skipping ThingsBoard send");
    return;
  }

  String payload = "{";
  payload += "\"temperature\":" + String(data.temperature, 2) + ",";
  payload += "\"turbidity\":" + String(data.turbidityNTU, 2) + ",";
  payload += "\"tds\":" + String(data.tds, 2) + ",";
  payload += "\"light\":" + String(data.light, 2) + ",";
  payload += "\"ph\":" + String(data.ph, 2) + ",";

  payload += "\"temperature_valid\":" + String(data.tempValid ? "true" : "false") + ",";
  payload += "\"tds_valid\":" + String(data.tdsValid ? "true" : "false") + ",";
  payload += "\"turbidity_valid\":" + String(data.turbidityValid ? "true" : "false") + ",";
  payload += "\"light_valid\":" + String(data.lightValid ? "true" : "false") + ",";
  payload += "\"ph_valid\":" + String(data.phValid ? "true" : "false");

  payload += "}";

  Serial.println("Sending to ThingsBoard:");
  Serial.println(payload);

  bool ok = tbClient.publish("v1/devices/me/telemetry", payload.c_str());
  Serial.print("ThingsBoard publish: ");
  Serial.println(ok ? "success" : "failed");
}

// ========================================================
// ALERTS
// ========================================================
void handleAlerts(const SensorData &data) {
  if (data.tempValid && data.temperature > TEMP_THRESHOLD_HIGH && !tempAlertSent) {
    String msg = "Fish Tank Alert\n";
    msg += "Temperature crossed threshold\n";
    msg += "Value: " + String(data.temperature, 2) + " C\n";
    msg += "Threshold: " + String(TEMP_THRESHOLD_HIGH, 2) + " C";
    sendTelegramMessage(msg);
    tempAlertSent = true;
  }
  if (!data.tempValid || data.temperature <= TEMP_THRESHOLD_HIGH) {
    tempAlertSent = false;
  }

  if (data.lightValid && data.light > LIGHT_THRESHOLD_HIGH && !lightAlertSent) {
    String msg = "Fish Tank Alert\n";
    msg += "Light crossed threshold\n";
    msg += "Value: " + String(data.light, 2) + " lux\n";
    msg += "Threshold: " + String(LIGHT_THRESHOLD_HIGH, 2) + " lux";
    sendTelegramMessage(msg);
    lightAlertSent = true;
  }
  if (!data.lightValid || data.light <= LIGHT_THRESHOLD_HIGH) {
    lightAlertSent = false;
  }

  if (data.phValid && data.ph < PH_THRESHOLD_LOW && !phLowAlertSent) {
    String msg = "Fish Tank Alert\n";
    msg += "pH below safe threshold\n";
    msg += "Value: " + String(data.ph, 2) + "\n";
    msg += "Threshold: " + String(PH_THRESHOLD_LOW, 2);
    sendTelegramMessage(msg);
    phLowAlertSent = true;
  }
  if (!data.phValid || data.ph >= PH_THRESHOLD_LOW) {
    phLowAlertSent = false;
  }

  if (data.phValid && data.ph > PH_THRESHOLD_HIGH && !phHighAlertSent) {
    String msg = "Fish Tank Alert\n";
    msg += "pH above safe threshold\n";
    msg += "Value: " + String(data.ph, 2) + "\n";
    msg += "Threshold: " + String(PH_THRESHOLD_HIGH, 2);
    sendTelegramMessage(msg);
    phHighAlertSent = true;
  }
  if (!data.phValid || data.ph <= PH_THRESHOLD_HIGH) {
    phHighAlertSent = false;
  }

  if (data.tdsValid && data.tds > TDS_THRESHOLD_HIGH && !tdsAlertSent) {
    String msg = "Fish Tank Alert\n";
    msg += "TDS crossed threshold\n";
    msg += "Value: " + String(data.tds, 2) + " ppm\n";
    msg += "Threshold: " + String(TDS_THRESHOLD_HIGH, 2) + " ppm";
    sendTelegramMessage(msg);
    tdsAlertSent = true;
  }
  if (!data.tdsValid || data.tds <= TDS_THRESHOLD_HIGH) {
    tdsAlertSent = false;
  }

  if (data.turbidityValid && data.turbidityNTU > TURBIDITY_THRESHOLD_HIGH && !turbidityAlertSent) {
    String msg = "Fish Tank Alert\n";
    msg += "Turbidity crossed threshold\n";
    msg += "Value: " + String(data.turbidityNTU, 2) + " NTU\n";
    msg += "Threshold: " + String(TURBIDITY_THRESHOLD_HIGH, 2) + " NTU";
    sendTelegramMessage(msg);
    turbidityAlertSent = true;
  }
  if (!data.turbidityValid || data.turbidityNTU <= TURBIDITY_THRESHOLD_HIGH) {
    turbidityAlertSent = false;
  }
}

// ========================================================
// SERIAL PRINT
// ========================================================
void printSensorData(const SensorData &data) {
  Serial.println("========================================");
  Serial.println("ESP32 Fish Tank Monitor Readings");
  Serial.println("========================================");

  if (data.tempValid) {
    Serial.print("Temperature : ");
    Serial.print(data.temperature, 2);
    Serial.println(" C");
  } else {
    Serial.println("Temperature : ERROR / DISCONNECTED");
  }

  if (data.tdsValid) {
    Serial.print("TDS         : ");
    Serial.print(data.tds, 2);
    Serial.println(" ppm");
  } else {
    Serial.print("TDS         : ERROR / INVALID | Raw ADC = ");
    Serial.println(data.rawTDS, 0);
  }

  if (data.lightValid) {
    Serial.print("Light       : ");
    Serial.print(data.light, 2);
    Serial.println(" lux");
  } else {
    Serial.println("Light       : ERROR / DISCONNECTED");
  }

  if (data.turbidityValid) {
    Serial.print("Turbidity   : ");
    Serial.print(data.turbidityNTU, 2);
    Serial.println(" NTU");
  } else {
    Serial.print("Turbidity   : ERROR / INVALID | Raw ADC = ");
    Serial.println(data.rawTurbidity, 0);
  }

  if (data.phValid) {
    Serial.print("pH          : ");
    Serial.println(data.ph, 2);
  } else {
    Serial.print("pH          : ERROR / INVALID | Raw ADC = ");
    Serial.println(data.rawPH, 0);
  }

  Serial.print("Timestamp   : ");
  Serial.println(data.timestamp);
  Serial.println("========================================");
}

// ========================================================
// SETUP
// ========================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("========================================");
  Serial.println("ESP32 Fish Tank Monitor");
  Serial.println("Backend + ThingsBoard + Telegram");
  Serial.println("========================================");

  connectWiFi();
  setupTime();

  Wire.begin(21, 22);
  bh1750Initialized = lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);

  if (bh1750Initialized) {
    Serial.println("BH1750 detected successfully!");
  } else {
    Serial.println("BH1750 NOT detected!");
  }

  pinMode(TDS_PIN, INPUT);
  pinMode(TURBIDITY_PIN, INPUT);
  pinMode(PH_PIN, INPUT);
  analogReadResolution(12);

  pinMode(TEMP_PIN, INPUT_PULLUP);
  tempSensor.begin();

  tbClient.setServer(tbServer, tbPort);

  Serial.println("Telegram settings:");
  Serial.print("Chat ID: ");
  Serial.println(telegramChatId);

  Serial.println("All sensors initialized.");
  Serial.println();
}

// ========================================================
// LOOP
// ========================================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!tbClient.connected()) {
    connectThingsBoard();
  }

  tbClient.loop();

  if (millis() - lastSendTime < sendInterval) {
    return;
  }

  lastSendTime = millis();

  SensorData data = readAllSensors();

  printSensorData(data);
  sendToBackend(data);
  sendToThingsBoard(data);
  handleAlerts(data);

  Serial.println();
}