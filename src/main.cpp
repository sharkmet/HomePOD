/**
 * HomePOD ESP32-D Sensor Firmware
 *
 * Sensors:
 *   - Microphone: GPIO35 (ADC input)
 *   - DHT22 Temperature/Humidity: GPIO4
 *   - BH1750 Light Sensor: GPIO21 (SDA), GPIO22 (SCL)
 */

#include <Arduino.h>
#include <Wire.h>
#include "sensors/microphone.h"
#include "sensors/dht_sensor.h"
#include "sensors/light_sensor.h"

// Sensor reading interval (ms)
#define SENSOR_READ_INTERVAL 2000
#define AUDIO_SAMPLE_INTERVAL 100

// Global sensor instances
MicrophoneSensor micSensor;
DHTSensor dhtSensor;
LightSensor lightSensor;

// Timing variables
unsigned long lastSensorRead = 0;
unsigned long lastAudioSample = 0;

// Sensor data structure
struct SensorData {
    float temperature;
    float humidity;
    float lightLevel;
    int audioLevel;
    int audioPeak;
    bool isValid;
} sensorData;

void printSensorData() {
    Serial.println("=== HomePOD Sensor Readings ===");

    Serial.printf("Temperature: %.1f°C\n", sensorData.temperature);
    Serial.printf("Humidity: %.1f%%\n", sensorData.humidity);
    Serial.printf("Light Level: %.1f lux\n", sensorData.lightLevel);
    Serial.printf("Audio Level: %d (Peak: %d)\n", sensorData.audioLevel, sensorData.audioPeak);

    Serial.println("================================");
    Serial.println();
}

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
