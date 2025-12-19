/**
 * Microphone Sensor Module
 * Analog microphone on GPIO35 (ADC1_CH7)
 */

#ifndef MICROPHONE_H
#define MICROPHONE_H

#include <Arduino.h>

// Pin configuration
#define MIC_PIN 35

// Audio sampling configuration
#define AUDIO_SAMPLES 64
#define AUDIO_NOISE_FLOOR 100

struct AudioReading {
    int level;      // Current audio level (0-4095)
    int peak;       // Peak level since last reset
    int average;    // Running average
    bool isValid;
};

class MicrophoneSensor {
public:
    MicrophoneSensor();

    /**
     * Initialize the microphone sensor
     * @return true if initialization successful
     */
    bool begin();

    /**
     * Read current audio level with peak detection
     * @return AudioReading struct with level data
     */
    AudioReading read();

    /**
     * Reset peak level tracking
     */
    void resetPeak();

    /**
     * Get current peak level
     * @return Peak audio level
     */
    int getPeak() const;

    /**
     * Check if audio level exceeds threshold
     * @param threshold Level to check against
     * @return true if current level exceeds threshold
     */
    bool isAboveThreshold(int threshold) const;

private:
    int _peakLevel;
    int _lastLevel;
    long _runningSum;
    int _sampleCount;

    /**
     * Sample the microphone multiple times and return statistics
     */
    void sampleAudio(int& minVal, int& maxVal, int& avgVal);
};

#endif // MICROPHONE_H
