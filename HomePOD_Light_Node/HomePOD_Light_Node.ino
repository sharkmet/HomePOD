/**
 * ============================================
 * HomePOD ESP32 Light Sensing Firmware
 * ============================================
 * REQUIRED ARDUINO IDE LIBRARIES:
 * 1. BH1750 by Christopher Laws (v1.3.0+)
 */

 #include <Arduino.h>
 #include <Wire.h>
 #include <BH1750.h>
 
 // PIN DEFINITIONS
 #define I2C_SDA_PIN 21
 #define I2C_SCL_PIN 22
 #define BH1750_ADDRESS 0x23
 
 #define SENSOR_READ_INTERVAL 2000
 
 // DATA STRUCTURES
 enum LightCondition {
     CONDITION_DARK, CONDITION_DIM, CONDITION_NORMAL, CONDITION_BRIGHT, CONDITION_VERY_BRIGHT
 };
 
 struct LightReading {
     float lux;
     LightCondition condition;
     bool isValid;
 };
 
 // LIGHT SENSOR CLASS
 class LightSensor {
 private:
     BH1750* _sensor;
     bool _initialized;
     float _lastLux;
 
     LightCondition getCondition(float lux) {
         if (lux < 10.0f) return CONDITION_DARK;
         else if (lux < 50.0f) return CONDITION_DIM;
         else if (lux < 300.0f) return CONDITION_NORMAL;
         else if (lux < 1000.0f) return CONDITION_BRIGHT;
         else return CONDITION_VERY_BRIGHT;
     }
 
 public:
     LightSensor() : _sensor(nullptr), _initialized(false), _lastLux(0.0f) {}
 
     bool begin() {
         _sensor = new BH1750(BH1750_ADDRESS);
         if (_sensor == nullptr) return false;
         _initialized = _sensor->begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
         if (_initialized) {
             delay(180);
             float lux = _sensor->readLightLevel();
             if (lux >= 0) _lastLux = lux;
         }
         return _initialized;
     }
 
     LightReading read() {
         LightReading reading;
         reading.isValid = false;
         if (!_initialized || _sensor == nullptr) return reading;
 
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
 unsigned long lastRead = 0;
 
 void setup() {
     Serial.begin(115200);
     delay(1000);
     Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
     
     if (lightSensor.begin()) Serial.println("HomePOD Light Node Initialized [OK]");
     else Serial.println("Light sensor initialization [FAIL]");
 }
 
 void loop() {
     if (millis() - lastRead >= SENSOR_READ_INTERVAL) {
         lastRead = millis();
         LightReading light = lightSensor.read();
         
         if (light.isValid) {
             Serial.printf("Light Level: %.1f lux\n", light.lux);
         }
     }
 }