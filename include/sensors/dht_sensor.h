/**
 * DHT Temperature/Humidity Sensor Module
 * DHT22/DHT11 on GPIO4
 */

#ifndef DHT_SENSOR_H
#define DHT_SENSOR_H

#include <Arduino.h>
#include <DHT.h>

// Pin configuration
#define DHT_PIN 4

// Sensor type (DHT22 is more accurate, change to DHT11 if using that)
#define DHT_TYPE DHT22

// Reading validation thresholds
#define TEMP_MIN -40.0f
#define TEMP_MAX 80.0f
#define HUMIDITY_MIN 0.0f
#define HUMIDITY_MAX 100.0f

struct DHTReading {
    float temperature;  // Temperature in Celsius
    float humidity;     // Relative humidity in %
    float heatIndex;    // Calculated heat index
    bool isValid;       // Whether reading is valid
};

class DHTSensor {
public:
    DHTSensor();

    /**
     * Initialize the DHT sensor
     * @return true if initialization successful
     */
    bool begin();

    /**
     * Read temperature and humidity
     * @return DHTReading struct with sensor data
     */
    DHTReading read();

    /**
     * Get temperature in Fahrenheit
     * @return Temperature in Fahrenheit
     */
    float getTemperatureF();

    /**
     * Check if sensor is responding
     * @return true if sensor is working
     */
    bool isConnected();

private:
    DHT* _dht;
    float _lastTemp;
    float _lastHumidity;
    bool _initialized;

    /**
     * Validate sensor reading
     */
    bool validateReading(float temp, float humidity);
};

#endif // DHT_SENSOR_H
