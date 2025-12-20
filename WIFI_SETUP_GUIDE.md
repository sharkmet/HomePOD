# HomePOD WiFi Setup Guide

Complete guide to send ESP32 sensor data to Raspberry Pi over WiFi.

---

## 📋 Overview

The ESP32 reads sensors every 2 seconds and sends data to your Raspberry Pi every 10 seconds via HTTP POST with JSON format.

**Data Flow:**
```
ESP32 Sensors → WiFi → Raspberry Pi Server → Web Dashboard / Log Files
```

---

## 🔧 Part 1: ESP32 Setup (Arduino IDE)

### Step 1: Install Additional Library

You need **one more library** for WiFi functionality:

1. Open Arduino IDE
2. Go to **Sketch → Include Library → Manage Libraries**
3. Search for **"ArduinoJson"**
4. Install **ArduinoJson by Benoit Blanchon** (v6.21.0 or later)

### Step 2: Update WiFi Credentials

Open `HomePOD_WiFi_Sensor_Firmware.ino` and change these lines (around line 62-66):

```cpp
// CHANGE THESE VALUES!
#define WIFI_SSID "YOUR_WIFI_SSID"           // Your WiFi network name
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"   // Your WiFi password
#define RASPBERRY_PI_IP "192.168.1.100"      // Your Pi's IP address (see Part 2)
#define DEVICE_NAME "HomePOD-Living-Room"    // Give your device a unique name
```

**Example:**
```cpp
#define WIFI_SSID "MyHomeNetwork"
#define WIFI_PASSWORD "MySecretPassword123"
#define RASPBERRY_PI_IP "192.168.1.50"
#define DEVICE_NAME "HomePOD-Bedroom"
```

### Step 3: Upload to ESP32

1. Select **Board**: ESP32 Dev Module
2. Select your **COM Port**
3. Click **Upload** (arrow button)
4. Open **Serial Monitor** (115200 baud) to see WiFi connection status

---

## 🖥️ Part 2: Raspberry Pi Setup

### Step 1: Find Raspberry Pi IP Address

SSH into your Raspberry Pi or open a terminal and run:

```bash
hostname -I
```

This will show your Pi's IP address (e.g., `192.168.1.50`). Use this IP in the ESP32 code above.

### Step 2: Install Python Dependencies

On your Raspberry Pi, run:

```bash
sudo apt update
sudo apt install python3-pip
pip3 install flask
```

### Step 3: Copy Server Script to Raspberry Pi

Transfer `raspberry_pi_server.py` to your Raspberry Pi. You can use one of these methods:

**Option A: Using SCP (from your PC)**
```bash
scp raspberry_pi_server.py pi@<raspberry-pi-ip>:~/
```

**Option B: Using nano (directly on Pi)**
```bash
nano ~/raspberry_pi_server.py
# Paste the contents and save (Ctrl+X, Y, Enter)
```

### Step 4: Run the Server

On your Raspberry Pi:

```bash
cd ~
python3 raspberry_pi_server.py
```

You should see:
```
============================================================
   HomePOD Sensor Data Receiver
   Raspberry Pi Server Starting...
============================================================

Server Configuration:
  - Port: 5000
  - Data log file: sensor_data.log
  - Latest data file: latest_sensor_data.json

To access the web interface:
  - Local: http://localhost:5000
  - Network: http://<raspberry-pi-ip>:5000

Press Ctrl+C to stop the server
============================================================
```

---

## 🌐 Part 3: View Your Data

### Web Dashboard

Open a web browser and go to:
```
http://<raspberry-pi-ip>:5000
```

You'll see a live dashboard with all sensor readings that auto-refreshes every 5 seconds.

### View Logged Data

All sensor data is saved to files on the Raspberry Pi:

```bash
# View latest readings
cat ~/latest_sensor_data.json

# View full log history
cat ~/sensor_data.log

# View last 20 readings
tail -n 20 ~/sensor_data.log
```

### API Endpoints

- `GET /` - Web dashboard
- `GET /latest` - Get latest data from all devices (JSON)
- `GET /latest/<device_name>` - Get latest data from specific device
- `POST /sensor-data` - Endpoint where ESP32 sends data

---

## 🔄 Auto-Start Server on Boot (Optional)

To make the server start automatically when Raspberry Pi boots:

### Create systemd service:

```bash
sudo nano /etc/systemd/system/homepod-server.service
```

Paste this content:

```ini
[Unit]
Description=HomePOD Sensor Data Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/raspberry_pi_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable homepod-server.service
sudo systemctl start homepod-server.service
```

Check status:
```bash
sudo systemctl status homepod-server.service
```

View logs:
```bash
sudo journalctl -u homepod-server.service -f
```

---

## 📊 JSON Data Format

The ESP32 sends data in this JSON format:

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
  },
  "received_at": "2024-01-15 14:30:45"
}
```

---

## 🐛 Troubleshooting

### ESP32 won't connect to WiFi

1. Check WiFi credentials are correct
2. Ensure WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
3. Check Serial Monitor for error messages
4. Verify WiFi router is nearby (good signal strength)

### ESP32 can't reach Raspberry Pi

1. Verify Raspberry Pi IP address with `hostname -I`
2. Ensure both devices are on the same network
3. Check firewall on Raspberry Pi:
   ```bash
   sudo ufw allow 5000
   ```
4. Test server is running:
   ```bash
   curl http://localhost:5000
   ```

### No data appearing on dashboard

1. Check ESP32 Serial Monitor for HTTP response codes
2. Verify server is running on Raspberry Pi
3. Check `sensor_data.log` file for incoming data
4. Ensure ESP32 and Pi clocks are reasonably accurate

### Server crashes or stops

1. Check Python error messages
2. Ensure Flask is installed: `pip3 install flask`
3. Check disk space: `df -h`
4. View system logs: `sudo journalctl -xe`

---

## 📈 Next Steps

Now that you have data flowing, you can:

1. **Add a database** - Store data in SQLite or InfluxDB
2. **Create graphs** - Use Grafana or plot data with matplotlib
3. **Add alerts** - Send notifications when thresholds are exceeded
4. **Mobile app** - Access data from your phone
5. **Multiple devices** - Add more ESP32 sensors around your home

---

## 📝 Files Summary

- `HomePOD_WiFi_Sensor_Firmware.ino` - ESP32 firmware with WiFi
- `raspberry_pi_server.py` - Python server for Raspberry Pi
- `sensor_data.log` - Timestamped log of all sensor readings
- `latest_sensor_data.json` - Most recent reading from each device

---

## 🆘 Need Help?

Check the Serial Monitor on ESP32 and terminal output on Raspberry Pi for detailed error messages and status information.
