/**
 * ============================================
 * HomePOD ESP32 Env Node (DHT22 + Mic)
 * Records data and sends JSON to Raspberry Pi
 * ============================================
 */
 #include <Arduino.h>
 #include <DHT.h>
 #include <WiFi.h>
 #include <HTTPClient.h>
 #include <ArduinoJson.h>
 
 // ============================================
 // CONFIGURATION - UPDATE THIS!
 // ============================================
#define WIFI_SSID "Netgear 2006"           // Change to your WiFi name
#define WIFI_PASSWORD "woaiPDMS59"   // Change to your WiFi password
#define RASPBERRY_PI_IP "10.0.0.47"      // Change to your Raspberry Pi IP address
#define RASPBERRY_PI_PORT 5000  
#define DEVICE_NAME "gurt"
 
 // PINS & SETTINGS
 #define MIC_PIN 35
 #define DHT_PIN 4
 #define DHT_TYPE DHT22
 
 #define AUDIO_SAMPLES 64
 #define AUDIO_NOISE_FLOOR 100
 #define WIFI_SEND_INTERVAL 10000 // Send data every 10 seconds
 
 // ============================================
 // SENSOR CLASSES
 // ============================================
 class DHTSensor {
 private:
     DHT* _dht;
     float _lastTemp;
     float _lastHumidity;
     bool _initialized;
 
     bool validateReading(float temp, float humidity) {
         if (isnan(temp) || isnan(humidity)) return false;
         if (temp < -40 || temp > 80) return false;
         if (humidity < 0 || humidity > 100) return false;
         return true;
     }
 
 public:
     DHTSensor() : _dht(nullptr), _lastTemp(0.0f), _lastHumidity(0.0f), _initialized(false) {}
 
     void begin() {
         _dht = new DHT(DHT_PIN, DHT_TYPE);
         _dht->begin();
         delay(2000); // Warmup
         _initialized = true;
     }
 
     bool read(float &temp, float &hum) {
         if (!_initialized) return false;
         float t = _dht->readTemperature();
         float h = _dht->readHumidity();
 
         if (validateReading(t, h)) {
             temp = _lastTemp = t;
             hum = _lastHumidity = h;
             return true;
         }
         return false;
     }
 };
 
 class MicrophoneSensor {
 private:
     int _peakLevel;
 
 public:
     MicrophoneSensor() : _peakLevel(0) {}
 
     void begin() {
         analogReadResolution(12);
         analogSetAttenuation(ADC_11db);
     }
 
     void sample() {
         int minVal = 4095;
         int maxVal = 0;
         
         // Fast sampling loop
         for (int i = 0; i < AUDIO_SAMPLES; i++) {
             int val = analogRead(MIC_PIN);
             if (val < minVal) minVal = val;
             if (val > maxVal) maxVal = val;
         }
 
         int peakToPeak = maxVal - minVal;
         // Noise floor correction
         if (peakToPeak < AUDIO_NOISE_FLOOR) peakToPeak = 0;
         else peakToPeak -= AUDIO_NOISE_FLOOR;
 
         if (peakToPeak > _peakLevel) _peakLevel = peakToPeak;
     }
 
     int getPeakAndReset() {
         int p = _peakLevel;
         _peakLevel = 0;
         return p;
     }
 };
 
 // ============================================
 // GLOBAL OBJECTS
 // ============================================
 DHTSensor dhtSensor;
 MicrophoneSensor micSensor;
 unsigned long lastSend = 0;
 unsigned long lastSample = 0;
 
 void connectWiFi() {
     Serial.print("Connecting to WiFi");
     WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
     while (WiFi.status() != WL_CONNECTED) {
         delay(500);
         Serial.print(".");
     }
     Serial.println("\nWiFi Connected!");
 }
 
 void sendData(float temp, float hum, int audioPeak) {
     if (WiFi.status() != WL_CONNECTED) {
         Serial.println("WiFi Disconnected. Reconnecting...");
         connectWiFi();
     }
 
     HTTPClient http;
     // URL for the Python Flask Server
     String url = "http://" + String(RASPBERRY_PI_IP) + ":5000/sensor-data";
     
     http.begin(url);
     http.addHeader("Content-Type", "application/json");
 
     // Match JSON structure to Python script
     StaticJsonDocument<256> doc;
     doc["device_name"] = DEVICE_NAME; // Changed from 'device'
     
     JsonObject s = doc.createNestedObject("sensors");
     s["temperature"] = temp;          // Changed from 'temp'
     s["humidity"] = hum;              // Changed from 'hum'
     s["audio_peak"] = audioPeak;
 
     String jsonString;
     serializeJson(doc, jsonString);
     
     int responseCode = http.POST(jsonString);
     if (responseCode > 0) Serial.printf("Sent Data (Code %d)\n", responseCode);
     else Serial.printf("Error Sending: %s\n", http.errorToString(responseCode).c_str());
     
     http.end();
 }
 
 // ============================================
 // MAIN LOOP
 // ============================================
 void setup() {
     Serial.begin(115200);
     dhtSensor.begin();
     micSensor.begin();
     connectWiFi();
     Serial.println("Env Node Initialized");
 }
 
 void loop() {
     unsigned long currentMillis = millis();
 
     // 1. High Frequency Audio Sampling (Every 100ms)
     if (currentMillis - lastSample >= 100) {
         lastSample = currentMillis;
         micSensor.sample();
     }
 
     // 2. Data Reporting (Every 10s)
     if (currentMillis - lastSend >= WIFI_SEND_INTERVAL) {
         lastSend = currentMillis;
         
         float t, h;
         if (dhtSensor.read(t, h)) {
             int peak = micSensor.getPeakAndReset();
             
             Serial.printf("Temp: %.1f C | Hum: %.1f %% | Audio Peak: %d\n", t, h, peak);
             sendData(t, h, peak);
         } else {
             Serial.println("Failed to read DHT sensor!");
         }
     }
 }