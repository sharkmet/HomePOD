/**
 * Light Sensor Implementation
 * BH1750 on I2C (GPIO21=SDA, GPIO22=SCL)
 */

#include "sensors/light_sensor.h"

LightSensor::LightSensor()
    : _sensor(nullptr)
    , _initialized(false)
    , _lastLux(0.0f) {
}

bool LightSensor::begin() {
    // Create BH1750 instance
    _sensor = new BH1750(BH1750_ADDRESS);

    if (_sensor == nullptr) {
        return false;
    }

    // Initialize the sensor
    // Using continuous high-resolution mode for best accuracy
    _initialized = _sensor->begin(BH1750::CONTINUOUS_HIGH_RES_MODE);

    if (_initialized) {
        // Wait for first measurement
        delay(180);  // BH1750 measurement time

        // Try to get a reading
        float lux = _sensor->readLightLevel();
        if (lux >= 0) {
            _lastLux = lux;
        }
    }

    return _initialized;
}

LightReading LightSensor::read() {
    LightReading reading;
    reading.isValid = false;

    if (!_initialized || _sensor == nullptr) {
        reading.lux = 0.0f;
        reading.condition = CONDITION_DARK;
        return reading;
    }

    // Read light level
    float lux = _sensor->readLightLevel();

    // BH1750 returns negative value on error
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

float LightSensor::getLux() {
    if (!_initialized || _sensor == nullptr) {
        return 0.0f;
    }

    float lux = _sensor->readLightLevel();
    if (lux >= 0) {
        _lastLux = lux;
        return lux;
    }

    return _lastLux;
}

LightCondition LightSensor::getCondition(float lux) {
    if (lux < LIGHT_DARK) {
        return CONDITION_DARK;
    } else if (lux < LIGHT_DIM) {
        return CONDITION_DIM;
    } else if (lux < LIGHT_NORMAL) {
        return CONDITION_NORMAL;
    } else if (lux < LIGHT_BRIGHT) {
        return CONDITION_BRIGHT;
    } else {
        return CONDITION_VERY_BRIGHT;
    }
}

const char* LightSensor::getConditionString(LightCondition condition) {
    switch (condition) {
        case CONDITION_DARK:
            return "Dark";
        case CONDITION_DIM:
            return "Dim";
        case CONDITION_NORMAL:
            return "Normal";
        case CONDITION_BRIGHT:
            return "Bright";
        case CONDITION_VERY_BRIGHT:
            return "Very Bright";
        default:
            return "Unknown";
    }
}

bool LightSensor::isConnected() {
    if (!_initialized || _sensor == nullptr) {
        return false;
    }

    // Try to read - BH1750 returns negative on error
    float lux = _sensor->readLightLevel();
    return (lux >= 0);
}

void LightSensor::setMode(BH1750::Mode mode) {
    if (_initialized && _sensor != nullptr) {
        _sensor->configure(mode);
    }
}
