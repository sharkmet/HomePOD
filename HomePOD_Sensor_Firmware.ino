/**
 * ============================================
 * HomePOD ESP32 Sensor Firmware
 * Single File Arduino IDE Version
 * ============================================
 *
 * REQUIRED ARDUINO IDE LIBRARIES:
 * --------------------------------
 * 1. DHT sensor library by Adafruit (v1.4.6+)
 *    - Go to: Sketch → Include Library → Manage Libraries
 *    - Search: "DHT sensor library"
 *    - Install by: Adafruit
 *
 * 2. Adafruit Unified Sensor by Adafruit (v1.1.14+)
 *    - Search: "Adafruit Unified Sensor"
 *    - Install by: Adafruit
 *    - NOTE: Required dependency for DHT library
 *
 * 3. BH1750 by Christopher Laws (v1.3.0+)
 *    - Search: "BH1750"
 *    - Install by: Christopher Laws (claws)
 *
 * HARDWARE CONNECTIONS:
 * ---------------------
 * ESP32-D Board:
 *   - Microphone (MAX4466): GPIO35 (ADC1_CH7)
 *   - DHT22 Sensor: GPIO4
 *   - BH1750 Light Sensor (I2C):
 *       - SDA: GPIO21
 *       - SCL: GPIO22
 *
 * UPLOAD SETTINGS:
 * ----------------
 * Board: ESP32 Dev Module
 * Upload Speed: 921600
 * CPU Frequency: 240MHz (WiFi/BT)
 * Flash Frequency: 80MHz
 * Flash Mode: QIO
 * Flash Size: 4MB
 * Partition Scheme: Default 4MB with spiffs
 * Core Debug Level: None
 * PSRAM: Disabled
 *
 * ============================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <DHT.h>
#include <BH1750.h>

// ============================================
// PIN DEFINITIONS
// ============================================
#define MIC_PIN 35          // MAX4466 Microphone on GPIO35 (ADC1_CH7)
#define DHT_PIN 4           // DHT22 on GPIO4
#define I2C_SDA_PIN 21      // I2C SDA for BH1750
#define I2C_SCL_PIN 22      // I2C SCL for BH1750

// ============================================
// SENSOR CONFIGURATION
// ============================================
// DHT Sensor
#define DHT_TYPE DHT22      // Change to DHT11 if using DHT11
#define TEMP_MIN -40.0f
#define TEMP_MAX 80.0f
#define HUMIDITY_MIN 0.0f
#define HUMIDITY_MAX 100.0f

// BH1750 Light Sensor
#define BH1750_ADDRESS 0x23  // Default address (0x5C if ADDR pin is HIGH)

// Light level thresholds (lux)
#define LIGHT_DARK 10.0f
#define LIGHT_DIM 50.0f
#define LIGHT_NORMAL 300.0f
#define LIGHT_BRIGHT 1000.0f
#define LIGHT_VERY_BRIGHT 10000.0f

// Microphone Audio Sampling
#define AUDIO_SAMPLES 64
#define AUDIO_NOISE_FLOOR 100

// Timing intervals (milliseconds)
#define SENSOR_READ_INTERVAL 2000   // Read temp/humidity/light every 2 seconds
#define AUDIO_SAMPLE_INTERVAL 100   // Sample audio every 100ms

// ============================================
// DATA STRUCTURES
// ============================================
enum LightCondition {
    CONDITION_DARK,
    CONDITION_DIM,
    CONDITION_NORMAL,
    CONDITION_BRIGHT,
    CONDITION_VERY_BRIGHT
};

struct DHTReading {
    float temperature;  // Temperature in Celsius
    float humidity;     // Relative humidity in %
    float heatIndex;    // Calculated heat index
    bool isValid;       // Whether reading is valid
};

struct LightReading {
    float lux;                  // Light level in lux
    LightCondition condition;   // Categorized light condition
    bool isValid;               // Whether reading is valid
};

struct AudioReading {
    int level;      // Current audio level (0-4095)
    int peak;       // Peak level since last reset
    int average;    // Running average
    bool isValid;
};

struct SensorData {
    float temperature;
    float humidity;
    float lightLevel;
    int audioLevel;
    int audioPeak;
    bool isValid;
};

// ============================================
// DHT SENSOR CLASS
// ============================================
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
        delay(2000);  // Wait for sensor to stabilize

        // Try to get initial reading
        float temp = _dht->readTemperature();
        float humidity = _dht->readHumidity();

        if (isnan(temp) || isnan(humidity)) {
            delay(2000);
            temp = _dht->readTemperature();
            humidity = _dht->readHumidity();
        }

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

        if (!_initialized || _dht == nullptr) {
            reading.temperature = 0.0f;
            reading.humidity = 0.0f;
            reading.heatIndex = 0.0f;
            return reading;
        }

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
            // Return last valid readings on error
            reading.temperature = _lastTemp;
            reading.humidity = _lastHumidity;
            reading.heatIndex = _dht->computeHeatIndex(_lastTemp, _lastHumidity, false);
            reading.isValid = false;
        }

        return reading;
    }

    float getTemperatureF() {
        if (!_initialized || _dht == nullptr) return 0.0f;
        float tempC = _dht->readTemperature();
        if (isnan(tempC)) tempC = _lastTemp;
        return (tempC * 9.0f / 5.0f) + 32.0f;
    }

    bool isConnected() {
        if (!_initialized || _dht == nullptr) return false;
        float temp = _dht->readTemperature();
        return !isnan(temp);
    }
};

// ============================================
// LIGHT SENSOR CLASS
// ============================================
class LightSensor {
private:
    BH1750* _sensor;
    bool _initialized;
    float _lastLux;

    LightCondition getCondition(float lux) {
        if (lux < LIGHT_DARK) return CONDITION_DARK;
        else if (lux < LIGHT_DIM) return CONDITION_DIM;
        else if (lux < LIGHT_NORMAL) return CONDITION_NORMAL;
        else if (lux < LIGHT_BRIGHT) return CONDITION_BRIGHT;
        else return CONDITION_VERY_BRIGHT;
    }

public:
    LightSensor() : _sensor(nullptr), _initialized(false), _lastLux(0.0f) {}

    bool begin() {
        _sensor = new BH1750(BH1750_ADDRESS);
        if (_sensor == nullptr) return false;

        // Initialize with continuous high-resolution mode
        _initialized = _sensor->begin(BH1750::CONTINUOUS_HIGH_RES_MODE);

        if (_initialized) {
            delay(180);  // Wait for first measurement
            float lux = _sensor->readLightLevel();
            if (lux >= 0) _lastLux = lux;
        }

        return _initialized;
    }

    LightReading read() {
        LightReading reading;
        reading.isValid = false;

        if (!_initialized || _sensor == nullptr) {
            reading.lux = 0.0f;
            reading.condition = CONDITION_DARK;
            return reading;
        }

        float lux = _sensor->readLightLevel();

        if (lux >= 0) {
            reading.lux = lux;
            reading.condition = getCondition(lux);
            reading.isValid = true;
            _lastLux = lux;
        } else {
            // Return last valid reading on error
            reading.lux = _lastLux;
            reading.condition = getCondition(_lastLux);
            reading.isValid = false;
        }

        return reading;
    }

    float getLux() {
        if (!_initialized || _sensor == nullptr) return 0.0f;
        float lux = _sensor->readLightLevel();
        if (lux >= 0) {
            _lastLux = lux;
            return lux;
        }
        return _lastLux;
    }

    const char* getConditionString(LightCondition condition) {
        switch (condition) {
            case CONDITION_DARK: return "Dark";
            case CONDITION_DIM: return "Dim";
            case CONDITION_NORMAL: return "Normal";
            case CONDITION_BRIGHT: return "Bright";
            case CONDITION_VERY_BRIGHT: return "Very Bright";
            default: return "Unknown";
        }
    }

    bool isConnected() {
        if (!_initialized || _sensor == nullptr) return false;
        float lux = _sensor->readLightLevel();
        return (lux >= 0);
    }

    void setMode(BH1750::Mode mode) {
        if (_initialized && _sensor != nullptr) {
            _sensor->configure(mode);
        }
    }
};

// ============================================
// MICROPHONE SENSOR CLASS
// ============================================
class MicrophoneSensor {
private:
    int _peakLevel;
    int _lastLevel;
    long _runningSum;
    int _sampleCount;

    void sampleAudio(int& minVal, int& maxVal, int& avgVal) {
        minVal = 4095;
        maxVal = 0;
        long sum = 0;

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
    MicrophoneSensor() : _peakLevel(0), _lastLevel(0), _runningSum(0), _sampleCount(0) {}

    bool begin() {
        analogReadResolution(12);           // 12-bit resolution (0-4095)
        analogSetAttenuation(ADC_11db);     // Full range 0-3.3V

        int testReading = analogRead(MIC_PIN);
        return (testReading >= 0 && testReading <= 4095);
    }

    AudioReading read() {
        AudioReading reading;
        int minVal, maxVal, avgVal;

        sampleAudio(minVal, maxVal, avgVal);

        int peakToPeak = maxVal - minVal;

        // Apply noise floor correction
        if (peakToPeak < AUDIO_NOISE_FLOOR) {
            peakToPeak = 0;
        } else {
            peakToPeak -= AUDIO_NOISE_FLOOR;
        }

        // Update peak tracking
        if (peakToPeak > _peakLevel) {
            _peakLevel = peakToPeak;
        }

        // Update running average
        _runningSum += peakToPeak;
        _sampleCount++;
        _lastLevel = peakToPeak;

        reading.level = peakToPeak;
        reading.peak = _peakLevel;
        reading.average = (_sampleCount > 0) ? (_runningSum / _sampleCount) : 0;
        reading.isValid = true;

        return reading;
    }

    void resetPeak() {
        _peakLevel = 0;
        _runningSum = 0;
        _sampleCount = 0;
    }

    int getPeak() const {
        return _peakLevel;
    }

    bool isAboveThreshold(int threshold) const {
        return _lastLevel > threshold;
    }
};

// ============================================
// GLOBAL OBJECTS
// ============================================
MicrophoneSensor micSensor;
DHTSensor dhtSensor;
LightSensor lightSensor;

SensorData sensorData;
unsigned long lastSensorRead = 0;
unsigned long lastAudioSample = 0;

// ============================================
// HELPER FUNCTIONS
// ============================================
void printSensorData() {
    Serial.println("=== HomePOD Sensor Readings ===");
    Serial.printf("Temperature: %.1f°C\n", sensorData.temperature);
    Serial.printf("Humidity: %.1f%%\n", sensorData.humidity);
    Serial.printf("Light Level: %.1f lux\n", sensorData.lightLevel);
    Serial.printf("Audio Level: %d (Peak: %d)\n", sensorData.audioLevel, sensorData.audioPeak);
    Serial.println("================================");
    Serial.println();
}

// ============================================
// ARDUINO SETUP
// ============================================
void setup() {
    // Initialize serial communication
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("================================");
    Serial.println("   HomePOD Sensor Firmware");
    Serial.println("   ESP32-D Initialization");
    Serial.println("================================");
    Serial.println();

    // Initialize I2C for light sensor
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    Serial.printf("I2C initialized on SDA=%d, SCL=%d\n", I2C_SDA_PIN, I2C_SCL_PIN);

    // Initialize sensors
    Serial.println("Initializing sensors...");

    if (micSensor.begin()) {
        Serial.printf("  [OK] Microphone on GPIO%d\n", MIC_PIN);
    } else {
        Serial.printf("  [FAIL] Microphone initialization failed\n");
    }

    if (dhtSensor.begin()) {
        Serial.printf("  [OK] DHT sensor on GPIO%d\n", DHT_PIN);
    } else {
        Serial.printf("  [FAIL] DHT sensor initialization failed\n");
    }

    if (lightSensor.begin()) {
        Serial.printf("  [OK] Light sensor (BH1750) on I2C\n");
    } else {
        Serial.printf("  [FAIL] Light sensor initialization failed\n");
    }

    Serial.println();
    Serial.println("Sensor initialization complete!");
    Serial.println("Starting sensor readings...");
    Serial.println();

    // Initialize sensor data
    memset(&sensorData, 0, sizeof(sensorData));
}

// ============================================
// ARDUINO MAIN LOOP
// ============================================
void loop() {
    unsigned long currentMillis = millis();

    // Sample audio more frequently for better peak detection
    if (currentMillis - lastAudioSample >= AUDIO_SAMPLE_INTERVAL) {
        lastAudioSample = currentMillis;

        AudioReading audioReading = micSensor.read();
        sensorData.audioLevel = audioReading.level;
        sensorData.audioPeak = audioReading.peak;
    }

    // Read environmental sensors at slower interval
    if (currentMillis - lastSensorRead >= SENSOR_READ_INTERVAL) {
        lastSensorRead = currentMillis;

        // Read DHT sensor
        DHTReading dhtReading = dhtSensor.read();
        if (dhtReading.isValid) {
            sensorData.temperature = dhtReading.temperature;
            sensorData.humidity = dhtReading.humidity;
        }

        // Read light sensor
        LightReading lightReading = lightSensor.read();
        if (lightReading.isValid) {
            sensorData.lightLevel = lightReading.lux;
        }

        // Reset audio peak after reporting
        micSensor.resetPeak();

        // Print all sensor data
        printSensorData();
    }
}
