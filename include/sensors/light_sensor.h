/**
 * Light Sensor Module
 * BH1750 on I2C (GPIO21=SDA, GPIO22=SCL)
 */

#ifndef LIGHT_SENSOR_H
#define LIGHT_SENSOR_H

#include <Arduino.h>
#include <Wire.h>
#include <BH1750.h>

// I2C Pin configuration
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22

// BH1750 I2C address (default 0x23, alternate 0x5C)
#define BH1750_ADDRESS 0x23

// Light level thresholds (lux)
#define LIGHT_DARK 10.0f
#define LIGHT_DIM 50.0f
#define LIGHT_NORMAL 300.0f
#define LIGHT_BRIGHT 1000.0f
#define LIGHT_VERY_BRIGHT 10000.0f

enum LightCondition {
    CONDITION_DARK,
    CONDITION_DIM,
    CONDITION_NORMAL,
    CONDITION_BRIGHT,
    CONDITION_VERY_BRIGHT
};

struct LightReading {
    float lux;              // Light level in lux
    LightCondition condition;  // Categorized light condition
    bool isValid;           // Whether reading is valid
};

class LightSensor {
public:
    LightSensor();

    /**
     * Initialize the light sensor
     * @return true if initialization successful
     */
    bool begin();

    /**
     * Read light level
     * @return LightReading struct with sensor data
     */
    LightReading read();

    /**
     * Get raw lux value
     * @return Light level in lux
     */
    float getLux();

    /**
     * Get categorized light condition
     * @param lux Light level to categorize
     * @return LightCondition enum value
     */
    LightCondition getCondition(float lux);

    /**
     * Get condition as string
     * @param condition LightCondition enum value
     * @return String description of condition
     */
    const char* getConditionString(LightCondition condition);

    /**
     * Check if sensor is responding
     * @return true if sensor is connected
     */
    bool isConnected();

    /**
     * Set measurement mode
     * @param mode BH1750 measurement mode
     */
    void setMode(BH1750::Mode mode);

private:
    BH1750* _sensor;
    bool _initialized;
    float _lastLux;
};

#endif // LIGHT_SENSOR_H
