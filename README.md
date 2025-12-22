# HomePOD - ESP32 Environmental Monitoring System

A comprehensive IoT sensor platform built on ESP32 for monitoring temperature, humidity, light levels, and ambient sound in your home or office.

## Features

- **Multi-Sensor Support**: Temperature, humidity, light intensity, and audio level monitoring
- **WiFi Connectivity**: Send sensor data to a Raspberry Pi server via HTTP
- **Real-Time Dashboard**: Web-based interface for live monitoring
- **Data Logging**: Automatic logging of all sensor readings
- **Modular Architecture**: Separate firmware options for different sensor configurations
- **Arduino IDE Compatible**: Easy to flash and modify

## Hardware Requirements

### ESP32 Module
- ESP32-D Development Board
- 4MB Flash Memory
- WiFi 2.4GHz capability

### Sensors
- **DHT22** - Temperature and Humidity Sensor (GPIO4)
- **BH1750** - Digital Light Sensor (I2C: SDA=GPIO21, SCL=GPIO22)
- **MAX4466** - Electret Microphone Amplifier (GPIO35)

### Wiring Diagram

```
ESP32-D Connections:
┌─────────────────────────────────────┐
│  GPIO4  ──────────── DHT22 (Data)  │
│  GPIO35 ──────────── MAX4466 (Out) │
│  GPIO21 ──────────── BH1750 (SDA)  │
│  GPIO22 ──────────── BH1750 (SCL)  │
│  3.3V   ──────────── Sensor VCC    │
│  GND    ──────────── Sensor GND    │
└─────────────────────────────────────┘
```

## Software Requirements

### Arduino IDE Libraries

Install these libraries via Arduino IDE Library Manager:

1. **DHT sensor library** by Adafruit (v1.4.6+)
2. **Adafruit Unified Sensor** by Adafruit (v1.1.14+)
3. **BH1750** by Christopher Laws (v1.3.0+)
4. **ArduinoJson** by Benoit Blanchon (v6.21.0+) _(for WiFi version only)_

### Raspberry Pi (Optional - for WiFi version)

- Python 3.x
- Flask (`pip3 install flask`)

## Available Firmware Options

### 1. Basic Sensor Firmware
**File**: `HomePOD_Sensor_Firmware.ino`

Standalone firmware that reads all sensors and outputs data to Serial Monitor. Perfect for testing and development.

**Features**:
- All sensor support
- Serial output every 2 seconds
- No WiFi required

### 2. WiFi-Enabled Firmware
**File**: `HomePOD_WiFi_Sensor_Firmware.ino`

Full-featured firmware with WiFi connectivity to send data to a Raspberry Pi server.

**Features**:
- All sensor support
- WiFi connectivity
- HTTP POST to Raspberry Pi
- Auto-reconnect on WiFi disconnect
- JSON data format
- Sends data every 10 seconds

**Setup Guide**: See [WIFI_SETUP_GUIDE.md](WIFI_SETUP_GUIDE.md)

### 3. Environmental Node
**File**: `HomePOD_Env_Node/HomePOD_Env_Node.ino`

Specialized firmware focusing on temperature and humidity monitoring.

**Features**:
- DHT22 sensor only
- Optimized for environmental monitoring
- Lower power consumption

### 4. Light Monitoring Node
**File**: `HomePOD_Light_Node/HomePOD_Light_Node.ino`

Dedicated light level monitoring with advanced features.

**Features**:
- BH1750 sensor only
- Light condition categorization (Dark, Dim, Normal, Bright, Very Bright)
- Configurable measurement modes

## Quick Start

### 1. Hardware Setup
1. Connect sensors to ESP32 according to wiring diagram above
2. Connect ESP32 to computer via USB

### 2. Software Installation
1. Install Arduino IDE
2. Add ESP32 board support:
   - Go to **File → Preferences**
   - Add to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to **Tools → Board → Boards Manager**
   - Install "esp32 by Espressif Systems"

3. Install required libraries (see Software Requirements above)

### 3. Upload Firmware
1. Open desired `.ino` file in Arduino IDE
2. Select **Board**: ESP32 Dev Module
3. Select your **COM Port**
4. Click **Upload**
5. Open **Serial Monitor** at 115200 baud

### 4. For WiFi Version (Optional)
1. Edit `HomePOD_WiFi_Sensor_Firmware.ino`:
   - Update WiFi SSID and password
   - Set Raspberry Pi IP address
2. Set up Raspberry Pi server (see [WIFI_SETUP_GUIDE.md](WIFI_SETUP_GUIDE.md))
3. Upload firmware and monitor connection

## Usage

### Serial Monitor Output (Basic Firmware)
```
================================
   HomePOD Sensor Firmware
   ESP32-D Initialization
================================

I2C initialized on SDA=21, SCL=22
Initializing sensors...
  [OK] Microphone on GPIO35
  [OK] DHT sensor on GPIO4
  [OK] Light sensor (BH1750) on I2C

Sensor initialization complete!
Starting sensor readings...

=== HomePOD Sensor Readings ===
Temperature: 23.5°C
Humidity: 45.2%
Light Level: 234.5 lux
Audio Level: 120 (Peak: 450)
================================
```

### Web Dashboard (WiFi Version)
Access the dashboard at `http://<raspberry-pi-ip>:5000`

Features:
- **Touch-friendly UI** optimized for 7-inch HDMI displays
- **Real-time sensor readings** with 10-second auto-refresh
- **Weather integration** with OpenWeatherMap (current + 5-day forecast)
- **To-Do List** with add, complete, and delete functionality (persistent storage)
- **Room grouping** for organizing multiple sensor nodes
- **Emoji icons** for visual room/weather identification
- JSON API endpoints

### Kiosk Mode Setup (Raspberry Pi)

To run the dashboard in full-screen kiosk mode on boot:

1. Install emoji font support:
   ```bash
   sudo apt install fonts-noto-color-emoji -y
   ```

2. Create autostart entry:
   ```bash
   sudo nano ~/.config/lxsession/LXDE-pi/autostart
   ```
   Add:
   ```
   @xset s off
   @xset -dpms
   @chromium-browser --kiosk --noerrdialogs http://localhost:5000
   ```

3. Set up server to start on boot:
   ```bash
   sudo nano /etc/systemd/system/homepod.service
   ```
   Add:
   ```ini
   [Unit]
   Description=HomePOD Dashboard Server
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/HomePOD/homepod_server_v2.py
   WorkingDirectory=/home/pi/HomePOD
   User=pi
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Enable: `sudo systemctl enable homepod.service`

4. Reboot: `sudo reboot`

## API Endpoints (WiFi Version)

- `GET /` - Web dashboard
- `GET /latest` - Latest data from all devices (JSON)
- `GET /latest/<device_name>` - Latest data from specific device
- `POST /sensor-data` - Endpoint for ESP32 data submission

### Example JSON Response
```json
{
  "device_name": "HomePOD-Living-Room",
  "timestamp": 45230,
  "sensors": {
    "temperature": 23.5,
    "humidity": 45.2,
    "light": 234.5,
    "audio_level": 120,
    "audio_peak": 450
  },
  "status": {
    "wifi_rssi": -45,
    "uptime_ms": 45230
  }
}
```

## Configuration

### Sensor Thresholds
Edit in the firmware to customize:

```cpp
// Temperature/Humidity ranges
#define TEMP_MIN -40.0f
#define TEMP_MAX 80.0f
#define HUMIDITY_MIN 0.0f
#define HUMIDITY_MAX 100.0f

// Light level thresholds (lux)
#define LIGHT_DARK 10.0f
#define LIGHT_DIM 50.0f
#define LIGHT_NORMAL 300.0f
#define LIGHT_BRIGHT 1000.0f

// Audio settings
#define AUDIO_SAMPLES 64
#define AUDIO_NOISE_FLOOR 100

// Timing intervals (milliseconds)
#define SENSOR_READ_INTERVAL 2000
#define WIFI_SEND_INTERVAL 10000
```

## Troubleshooting

### Sensors Not Detected
- Check wiring connections
- Verify sensor power (3.3V)
- Ensure I2C pull-up resistors if using long wires
- Check sensor I2C address (BH1750 default: 0x23)

### WiFi Connection Issues
- Verify WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Check SSID and password are correct
- Ensure ESP32 is within WiFi range
- Check Serial Monitor for detailed error messages

### Sensor Reading Errors
- DHT22 requires 2 seconds stabilization time
- BH1750 needs 180ms for first measurement
- Verify sensor voltage (3.3V for ESP32)

## Project Structure

```
HomePOD/
├── HomePOD_Sensor_Firmware.ino          # Basic all-sensor firmware
├── HomePOD_WiFi_Sensor_Firmware.ino     # WiFi-enabled firmware
├── HomePOD_Env_Node/                    # Environmental monitoring node
│   └── HomePOD_Env_Node.ino
├── HomePOD_Light_Node/                  # Light monitoring node
│   └── HomePOD_Light_Node.ino
├── raspberry_pi_server.py               # Python server for Raspberry Pi
├── WIFI_SETUP_GUIDE.md                  # WiFi setup instructions
├── src/                                 # PlatformIO source files
├── include/                             # PlatformIO headers
└── README.md                            # This file
```

## Advanced Features

### Multiple Device Support
The WiFi version supports multiple ESP32 devices reporting to the same Raspberry Pi server. Each device should have a unique `DEVICE_NAME` configured in the firmware.

### Auto-Start Server on Boot
Configure the Raspberry Pi server to start automatically on boot using systemd. See [WIFI_SETUP_GUIDE.md](WIFI_SETUP_GUIDE.md) for instructions.

### Data Export
All sensor data is logged to `sensor_data.log` on the Raspberry Pi in JSON format, ready for analysis or import into other tools.

## Future Enhancements

- [ ] MQTT support for Home Assistant integration
- [ ] Mobile app for iOS/Android
- [ ] Database storage (SQLite/InfluxDB)
- [ ] Grafana dashboard integration
- [ ] Alert notifications (email/SMS)
- [ ] Battery power optimization
- [ ] Deep sleep mode
- [ ] OTA (Over-The-Air) firmware updates

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open source and available for personal and educational use.

## Credits

**Authors**: Ryan Li, Gary Sun, Ryan Wang, Ryan Giang
**Repository**: [https://github.com/sharkmet/HomePOD](https://github.com/sharkmet/HomePOD)

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the [WIFI_SETUP_GUIDE.md](WIFI_SETUP_GUIDE.md) for setup help

---

**Built with**:
- ESP32-D Microcontroller
- Arduino Framework
- Adafruit Sensor Libraries
- Flask Web Framework
