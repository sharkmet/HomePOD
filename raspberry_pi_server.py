#!/usr/bin/env python3
"""
HomePOD Sensor Data Receiver
Simple Flask server for Raspberry Pi to receive sensor data from ESP32

Installation on Raspberry Pi:
    sudo apt update
    sudo apt install python3-pip
    pip3 install flask

Usage:
    python3 raspberry_pi_server.py

The server will run on port 5000 and accept sensor data from ESP32 devices.
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)

# Configuration
DATA_LOG_FILE = "sensor_data.log"
LATEST_DATA_FILE = "latest_sensor_data.json"

# Store latest readings in memory
latest_readings = {}

@app.route('/')
def home():
    """Home page with status information"""
    html = """
    <html>
    <head>
        <title>HomePOD Sensor Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            h1 { color: #333; }
            .sensor-card { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
            .value { font-size: 24px; font-weight: bold; color: #4CAF50; }
            .label { color: #666; font-size: 14px; }
            .timestamp { color: #999; font-size: 12px; font-style: italic; }
            .status { color: #4CAF50; font-weight: bold; }
        </style>
        <meta http-equiv="refresh" content="5">
    </head>
    <body>
        <div class="container">
            <h1>🏠 HomePOD Sensor Server</h1>
            <p class="status">✓ Server Running</p>
            <p>Listening for sensor data on port 5000</p>
            <hr>
    """

    if latest_readings:
        html += "<h2>Latest Sensor Readings</h2>"
        for device_name, data in latest_readings.items():
            sensors = data.get('sensors', {})
            timestamp = data.get('received_at', 'Unknown')

            html += f"""
            <div class="sensor-card">
                <h3>{device_name}</h3>
                <p class="timestamp">Last updated: {timestamp}</p>
                <table>
                    <tr>
                        <td class="label">Temperature:</td>
                        <td class="value">{sensors.get('temperature', 'N/A')}°C</td>
                    </tr>
                    <tr>
                        <td class="label">Humidity:</td>
                        <td class="value">{sensors.get('humidity', 'N/A')}%</td>
                    </tr>
                    <tr>
                        <td class="label">Light Level:</td>
                        <td class="value">{sensors.get('light', 'N/A')} lux</td>
                    </tr>
                    <tr>
                        <td class="label">Audio Level:</td>
                        <td class="value">{sensors.get('audio_level', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">Audio Peak:</td>
                        <td class="value">{sensors.get('audio_peak', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            """
    else:
        html += "<p>No sensor data received yet. Waiting for ESP32 to send data...</p>"

    html += """
            <hr>
            <h3>API Endpoints</h3>
            <ul>
                <li><a href="/latest">/latest</a> - Get latest sensor data (JSON)</li>
                <li><a href="/sensor-data">/sensor-data</a> - POST endpoint for ESP32</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    """Endpoint to receive sensor data from ESP32"""
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400

        # Add timestamp
        data['received_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Get device name
        device_name = data.get('device_name', 'Unknown Device')

        # Store in memory
        latest_readings[device_name] = data

        # Log to file
        with open(DATA_LOG_FILE, 'a') as f:
            f.write(json.dumps(data) + '\n')

        # Save latest data to JSON file
        with open(LATEST_DATA_FILE, 'w') as f:
            json.dump(latest_readings, f, indent=2)

        # Print to console
        print(f"\n{'='*50}")
        print(f"Received data from: {device_name}")
        print(f"Time: {data['received_at']}")
        if 'sensors' in data:
            sensors = data['sensors']
            print(f"Temperature: {sensors.get('temperature', 'N/A')}°C")
            print(f"Humidity: {sensors.get('humidity', 'N/A')}%")
            print(f"Light: {sensors.get('light', 'N/A')} lux")
            print(f"Audio Level: {sensors.get('audio_level', 'N/A')}")
            print(f"Audio Peak: {sensors.get('audio_peak', 'N/A')}")
        print(f"{'='*50}\n")

        return jsonify({
            'status': 'success',
            'message': 'Data received successfully',
            'device_name': device_name
        }), 200

    except Exception as e:
        print(f"Error processing sensor data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/latest', methods=['GET'])
def get_latest_data():
    """Get the latest sensor data for all devices"""
    return jsonify(latest_readings), 200

@app.route('/latest/<device_name>', methods=['GET'])
def get_device_latest(device_name):
    """Get the latest sensor data for a specific device"""
    if device_name in latest_readings:
        return jsonify(latest_readings[device_name]), 200
    else:
        return jsonify({'status': 'error', 'message': 'Device not found'}), 404

if __name__ == '__main__':
    print("\n" + "="*60)
    print("   HomePOD Sensor Data Receiver")
    print("   Raspberry Pi Server Starting...")
    print("="*60)
    print("\nServer Configuration:")
    print(f"  - Port: 5000")
    print(f"  - Data log file: {DATA_LOG_FILE}")
    print(f"  - Latest data file: {LATEST_DATA_FILE}")
    print("\nTo access the web interface:")
    print("  - Local: http://localhost:5000")
    print("  - Network: http://<raspberry-pi-ip>:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")

    # Run the Flask server
    # host='0.0.0.0' makes it accessible from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=False)
