/**
 * ============================================
 * HomePOD ESP32 Environmental & Audio Firmware
 * ============================================
 * REQUIRED ARDUINO IDE LIBRARIES:
 * 1. DHT sensor library by Adafruit (v1.4.6+)
 * 2. Adafruit Unified Sensor by Adafruit (v1.1.14+)
 */

 #include <Arduino.h>
 #include <DHT.h>
 
 // PIN DEFINITIONS
 #define MIC_PIN 35          // MAX4466 Microphone on GPIO35 (ADC1_CH7)
 #define DHT_PIN 4           // DHT22 on GPIO4
 
 // SENSOR CONFIGURATION
 #define DHT_TYPE DHT22      
 #define TEMP_MIN -40.0f
 #define TEMP_MAX 80.0f
 #define HUMIDITY_MIN 0.0f
 #define HUMIDITY_MAX 100.0f
 
 #define AUDIO_SAMPLES 64
 #define AUDIO_NOISE_FLOOR 100
 
 #define SENSOR_READ_INTERVAL 2000   
 #define AUDIO_SAMPLE_INTERVAL 100   
 
 // DATA STRUCTURES
 struct DHTReading {
     float temperature;
     float humidity;
     float heatIndex;
     bool isValid;
 };
 
 struct AudioReading {
     int level;
     int peak;
     int average;
     bool isValid;
 };
 
 struct SensorData {
     float temperature;
     float humidity;
     int audioLevel;
     int audioPeak;
     bool isValid;
 };
 
 // DHT SENSOR CLASS
 class DHTSensor {
 private:
     DHT* _dht;
     float _lastTemp;
     float _lastHumidity;
     bool _initialized;
 
     bool validateReading(float temp, float humidity) {
         if (isnan(temp) || isnan(humidity)) return false;
         if (temp < TEMP_MIN || temp > TEMP_MAX) return false;
         if (humidity < HUMIDITY_MIN || humidity > HUMIDITY_MAX) return false;
         return true;
     }
 
 public:
     DHTSensor() : _dht(nullptr), _lastTemp(0.0f), _lastHumidity(0.0f), _initialized(false) {}
 
     bool begin() {
         _dht = new DHT(DHT_PIN, DHT_TYPE);
         if (_dht == nullptr) return false;
         _dht->begin();
         delay(2000);
         float temp = _dht->readTemperature();
         float humidity = _dht->readHumidity();
         _initialized = !isnan(temp) && !isnan(humidity);
         if (_initialized) {
             _lastTemp = temp;
             _lastHumidity = humidity;
         }
         return _initialized;
     }
 
     DHTReading read() {
         DHTReading reading;
         reading.isValid = false;
         if (!_initialized || _dht == nullptr) return reading;
 
         float temp = _dht->readTemperature();
         float humidity = _dht->readHumidity();
 
         if (validateReading(temp, humidity)) {
             reading.temperature = temp;
             reading.humidity = humidity;
             reading.heatIndex = _dht->computeHeatIndex(temp, humidity, false);
             reading.isValid = true;
             _lastTemp = temp;
             _lastHumidity = humidity;
         } else {
             reading.temperature = _lastTemp;
             reading.humidity = _lastHumidity;
             reading.heatIndex = _dht->computeHeatIndex(_lastTemp, _lastHumidity, false);
         }
         return reading;
     }
 };
 
 // MICROPHONE SENSOR CLASS
 class MicrophoneSensor {
 private:
     int _peakLevel;
     long _runningSum;
     int _sampleCount;
 
     void sampleAudio(int& minVal, int& maxVal, int& avgVal) {
         minVal = 4095; maxVal = 0; long sum = 0;
         for (int i = 0; i < AUDIO_SAMPLES; i++) {
             int sample = analogRead(MIC_PIN);
             if (sample < minVal) minVal = sample;
             if (sample > maxVal) maxVal = sample;
             sum += sample;
             delayMicroseconds(100);
         }
         avgVal = sum / AUDIO_SAMPLES;
     }
 
 public:
     MicrophoneSensor() : _peakLevel(0), _runningSum(0), _sampleCount(0) {}
 
     bool begin() {
         analogReadResolution(12);
         analogSetAttenuation(ADC_11db);
         return (analogRead(MIC_PIN) >= 0);
     }
 
     AudioReading read() {
         AudioReading reading;
         int minVal, maxVal, avgVal;
         sampleAudio(minVal, maxVal, avgVal);
         int peakToPeak = maxVal - minVal;
         if (peakToPeak < AUDIO_NOISE_FLOOR) peakToPeak = 0;
         else peakToPeak -= AUDIO_NOISE_FLOOR;
 
         if (peakToPeak > _peakLevel) _peakLevel = peakToPeak;
         _runningSum += peakToPeak;
         _sampleCount++;
 
         reading.level = peakToPeak;
         reading.peak = _peakLevel;
         reading.average = (_sampleCount > 0) ? (_runningSum / _sampleCount) : 0;
         reading.isValid = true;
         return reading;
     }
 
     void resetPeak() { _peakLevel = 0; _runningSum = 0; _sampleCount = 0; }
 };
 
 // GLOBAL OBJECTS
 MicrophoneSensor micSensor;
 DHTSensor dhtSensor;
 SensorData sensorData;
 unsigned long lastSensorRead = 0;
 unsigned long lastAudioSample = 0;
 
 void setup() {
     Serial.begin(115200);
     delay(1000);
     Serial.println("\nHomePOD Environmental Node Initialized");
 
     if (micSensor.begin()) Serial.printf("  [OK] Mic on GPIO%d\n", MIC_PIN);
     if (dhtSensor.begin()) Serial.printf("  [OK] DHT on GPIO%d\n", DHT_PIN);
 }
 
 void loop() {
     unsigned long currentMillis = millis();
 
     if (currentMillis - lastAudioSample >= AUDIO_SAMPLE_INTERVAL) {
         lastAudioSample = currentMillis;
         AudioReading audio = micSensor.read();
         sensorData.audioLevel = audio.level;
         sensorData.audioPeak = audio.peak;
     }
 
     if (currentMillis - lastSensorRead >= SENSOR_READ_INTERVAL) {
         lastSensorRead = currentMillis;
         DHTReading dht = dhtSensor.read();
         if (dht.isValid) {
             sensorData.temperature = dht.temperature;
             sensorData.humidity = dht.humidity;
         }
 
         Serial.printf("Temp: %.1fC | Hum: %.1f%% | Audio Peak: %d\n", 
                       sensorData.temperature, sensorData.humidity, sensorData.audioPeak);
         
         micSensor.resetPeak();
     }
 }