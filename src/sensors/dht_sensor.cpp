/**
 * DHT Temperature/Humidity Sensor Implementation
 * DHT22/DHT11 on GPIO4
 */

#include "sensors/dht_sensor.h"

DHTSensor::DHTSensor()
    : _dht(nullptr)
    , _lastTemp(0.0f)
    , _lastHumidity(0.0f)
    , _initialized(false) {
}

bool DHTSensor::begin() {
    // Create DHT instance
    _dht = new DHT(DHT_PIN, DHT_TYPE);

    if (_dht == nullptr) {
        return false;
    }

    // Initialize DHT sensor
    _dht->begin();

    // Wait for sensor to stabilize
    delay(2000);

    // Try to get a reading to verify sensor is working
    float temp = _dht->readTemperature();
    float humidity = _dht->readHumidity();

    if (isnan(temp) || isnan(humidity)) {
        // First reading often fails, try once more
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

bool DHTSensor::validateReading(float temp, float humidity) {
    // Check for NaN
    if (isnan(temp) || isnan(humidity)) {
        return false;
    }

    // Check temperature range
    if (temp < TEMP_MIN || temp > TEMP_MAX) {
        return false;
    }

    // Check humidity range
    if (humidity < HUMIDITY_MIN || humidity > HUMIDITY_MAX) {
        return false;
    }

    return true;
}

DHTReading DHTSensor::read() {
    DHTReading reading;
    reading.isValid = false;

    if (!_initialized || _dht == nullptr) {
        reading.temperature = 0.0f;
        reading.humidity = 0.0f;
        reading.heatIndex = 0.0f;
        return reading;
    }

    // Read temperature and humidity
    float temp = _dht->readTemperature();
    float humidity = _dht->readHumidity();

    // Validate reading
    if (validateReading(temp, humidity)) {
        reading.temperature = temp;
        reading.humidity = humidity;
        reading.heatIndex = _dht->computeHeatIndex(temp, humidity, false);
        reading.isValid = true;

        // Store last valid readings
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

float DHTSensor::getTemperatureF() {
    if (!_initialized || _dht == nullptr) {
        return 0.0f;
    }

    float tempC = _dht->readTemperature();
    if (isnan(tempC)) {
        tempC = _lastTemp;
    }

    // Convert to Fahrenheit
    return (tempC * 9.0f / 5.0f) + 32.0f;
}

bool DHTSensor::isConnected() {
    if (!_initialized || _dht == nullptr) {
        return false;
    }

    // Try to read - if we get valid data, sensor is connected
    float temp = _dht->readTemperature();
    return !isnan(temp);
}
