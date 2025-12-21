/**
 * ============================================
 * HomePOD ESP32 Light Sensing Firmware
 * ============================================
 * REQUIRED ARDUINO IDE LIBRARIES:
 * 1. BH1750 by Christopher Laws (v1.3.0+)
 * 2. ArduinoJson by Benoit Blanchon
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include <BH1750.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <Wire.h>

// ============================================
// CONFIGURATION
// ============================================
#define WIFI_SSID "Netgear 2006"    // Copied from Env Node
#define WIFI_PASSWORD "woaiPDMS59"  // Copied from Env Node
#define RASPBERRY_PI_IP "10.0.0.47" // Copied from Env Node
#define RASPBERRY_PI_PORT 5000
#define DEVICE_NAME "HomePOD_Light_Node"

// PIN DEFINITIONS
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22
#define BH1750_ADDRESS 0x23

#define SENSOR_READ_INTERVAL 10000 // Match server reporting interval (10s)

// DATA STRUCTURES
enum LightCondition {
  CONDITION_DARK,
  CONDITION_DIM,
  CONDITION_NORMAL,
  CONDITION_BRIGHT,
  CONDITION_VERY_BRIGHT
};

struct LightReading {
  float lux;
  LightCondition condition;
  bool isValid;
};

// LIGHT SENSOR CLASS
class LightSensor {
private:
  BH1750 *_sensor;
  bool _initialized;
  float _lastLux;

  LightCondition getCondition(float lux) {
    if (lux < 10.0f)
      return CONDITION_DARK;
    else if (lux < 50.0f)
      return CONDITION_DIM;
    else if (lux < 300.0f)
      return CONDITION_NORMAL;
    else if (lux < 1000.0f)
      return CONDITION_BRIGHT;
    else
      return CONDITION_VERY_BRIGHT;
  }

public:
  LightSensor() : _sensor(nullptr), _initialized(false), _lastLux(0.0f) {}

  bool begin() {
    _sensor = new BH1750(BH1750_ADDRESS);
    if (_sensor == nullptr)
      return false;
    _initialized = _sensor->begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
    if (_initialized) {
      delay(180);
      float lux = _sensor->readLightLevel();
      if (lux >= 0)
        _lastLux = lux;
    }
    return _initialized;
  }

  LightReading read() {
    LightReading reading;
    reading.isValid = false;
    if (!_initialized || _sensor == nullptr)
      return reading;

    float lux = _sensor->readLightLevel();
    if (lux >= 0) {
      reading.lux = lux;
      reading.condition = getCondition(lux);
      reading.isValid = true;
      _lastLux = lux;
    } else {
      reading.lux = _lastLux;
      reading.condition = getCondition(_lastLux);
    }
    return reading;
  }
};

// GLOBAL OBJECTS
LightSensor lightSensor;
unsigned long lastSend = 0;

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
}

void sendData(float lux) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi Disconnected. Reconnecting...");
    connectWiFi();
  }

  HTTPClient http;
  // URL for the Python Flask Server
  String url = "http://" + String(RASPBERRY_PI_IP) + ":5000/sensor-data";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  // Create JSON payload
  StaticJsonDocument<256> doc;
  doc["device_name"] = DEVICE_NAME;

  JsonObject s = doc.createNestedObject("sensors");
  s["light"] = lux;

  // Add placeholder values for other fields if needed, or leave them out
  // (Server code uses .get() so it handles missing keys gracefully)

  String jsonString;
  serializeJson(doc, jsonString);

  int responseCode = http.POST(jsonString);
  if (responseCode > 0)
    Serial.printf("Sent Data (Code %d)\n", responseCode);
  else
    Serial.printf("Error Sending: %s\n",
                  http.errorToString(responseCode).c_str());

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Initialize I2C for Light Sensor
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

  if (lightSensor.begin())
    Serial.println("HomePOD Light Node Initialized [OK]");
  else
    Serial.println("Light sensor initialization [FAIL]");

  // Initialize WiFi
  connectWiFi();
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastSend >= SENSOR_READ_INTERVAL) {
    lastSend = currentMillis;

    LightReading light = lightSensor.read();

    if (light.isValid) {
      Serial.printf("Light Level: %.1f lux\n", light.lux);
      sendData(light.lux);
    } else {
      Serial.println("Failed to read Light sensor!");
    }
  }
}