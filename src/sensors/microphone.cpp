/**
 * Microphone Sensor Implementation
 * Analog microphone on GPIO35 (ADC1_CH7)
 */

#include "sensors/microphone.h"

MicrophoneSensor::MicrophoneSensor()
    : _peakLevel(0)
    , _lastLevel(0)
    , _runningSum(0)
    , _sampleCount(0) {
}

bool MicrophoneSensor::begin() {
    // Configure ADC for microphone pin
    // GPIO35 is ADC1_CH7 - analog input only, no pull-up/down needed
    analogReadResolution(12);  // 12-bit resolution (0-4095)
    analogSetAttenuation(ADC_11db);  // Full range 0-3.3V

    // Take a test reading
    int testReading = analogRead(MIC_PIN);

    // Basic validation - should get some reading
    return (testReading >= 0 && testReading <= 4095);
}

void MicrophoneSensor::sampleAudio(int& minVal, int& maxVal, int& avgVal) {
    minVal = 4095;
    maxVal = 0;
    long sum = 0;

    // Take multiple samples for accurate peak-to-peak measurement
    for (int i = 0; i < AUDIO_SAMPLES; i++) {
        int sample = analogRead(MIC_PIN);

        if (sample < minVal) minVal = sample;
        if (sample > maxVal) maxVal = sample;
        sum += sample;

        // Small delay between samples for better distribution
        delayMicroseconds(100);
    }

    avgVal = sum / AUDIO_SAMPLES;
}

AudioReading MicrophoneSensor::read() {
    AudioReading reading;
    int minVal, maxVal, avgVal;

    // Sample the microphone
    sampleAudio(minVal, maxVal, avgVal);

    // Calculate peak-to-peak amplitude (audio level)
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

    // Store last level
    _lastLevel = peakToPeak;

    // Fill reading structure
    reading.level = peakToPeak;
    reading.peak = _peakLevel;
    reading.average = (_sampleCount > 0) ? (_runningSum / _sampleCount) : 0;
    reading.isValid = true;

    return reading;
}

void MicrophoneSensor::resetPeak() {
    _peakLevel = 0;
    _runningSum = 0;
    _sampleCount = 0;
}

int MicrophoneSensor::getPeak() const {
    return _peakLevel;
}

bool MicrophoneSensor::isAboveThreshold(int threshold) const {
    return _lastLevel > threshold;
}
