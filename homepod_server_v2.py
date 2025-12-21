#!/usr/bin/env python3
"""
HomePOD Sensor Server v2
- Combines all nodes into a single dashboard
- Interprets raw sensor values into human-readable levels
- Dynamically displays only available sensor data
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

DATA_LOG_FILE = "sensor_data_v2.log"
latest_readings = {}

# ============================================
# SENSOR INTERPRETATION FUNCTIONS
# ============================================
def interpret_audio(audio_peak):
    """Convert raw audio peak to human-readable level"""
    if audio_peak is None:
        return None
    if audio_peak <= 50:
        return "Quiet"
    elif audio_peak <= 500:
        return "Talking"
    else:
        return "Loud"

def interpret_light(lux):
    """Convert lux value to human-readable level"""
    if lux is None:
        return None
    if lux < 50:
        return "Dark"
    elif lux <= 500:
        return "Bright"
    else:
        return "Very Bright"

# ============================================
# WEB ROUTES
# ============================================
@app.route('/')
def home():
    html = """
    <html>
    <head>
        <title>HomePOD Dashboard</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
                padding: 40px;
                color: #eee;
            }
            h1 {
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 10px;
                background: linear-gradient(90deg, #00d9ff, #00ff88);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle {
                text-align: center;
                color: #888;
                margin-bottom: 40px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                max-width: 1200px;
                margin: 0 auto;
            }
            .card {
                background: rgba(255,255,255,0.05);
                border-radius: 16px;
                padding: 24px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .card:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 30px rgba(0,217,255,0.2);
            }
            .card h3 {
                font-size: 1.3em;
                margin-bottom: 8px;
                color: #00d9ff;
            }
            .card .timestamp {
                font-size: 0.75em;
                color: #666;
                margin-bottom: 16px;
            }
            .sensor-row {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            .sensor-row:last-child { border-bottom: none; }
            .sensor-label { color: #aaa; }
            .sensor-value { font-weight: bold; color: #00ff88; }
            .no-data {
                text-align: center;
                padding: 60px;
                color: #666;
            }
            .status-dot {
                display: inline-block;
                width: 10px;
                height: 10px;
                background: #00ff88;
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        </style>
        <meta http-equiv="refresh" content="5">
    </head>
    <body>
        <h1>🏠 HomePOD Dashboard</h1>
        <p class="subtitle"><span class="status-dot"></span>Live sensor data</p>
        <div class="grid">
    """

    if latest_readings:
        for device_name, data in latest_readings.items():
            sensors = data.get('sensors', {})
            timestamp = data.get('received_at', 'Unknown')

            html += f"""
            <div class="card">
                <h3>{device_name}</h3>
                <p class="timestamp">Last updated: {timestamp}</p>
            """

            # Temperature (if available)
            if 'temperature' in sensors and sensors['temperature'] is not None:
                html += f"""
                <div class="sensor-row">
                    <span class="sensor-label">Temperature</span>
                    <span class="sensor-value">{sensors['temperature']:.1f}°C</span>
                </div>
                """

            # Humidity (if available)
            if 'humidity' in sensors and sensors['humidity'] is not None:
                html += f"""
                <div class="sensor-row">
                    <span class="sensor-label">Humidity</span>
                    <span class="sensor-value">{sensors['humidity']:.1f}%</span>
                </div>
                """

            # Audio Level (interpreted, if available)
            if 'audio_peak' in sensors and sensors['audio_peak'] is not None:
                audio_label = interpret_audio(sensors['audio_peak'])
                html += f"""
                <div class="sensor-row">
                    <span class="sensor-label">Audio Level</span>
                    <span class="sensor-value">{audio_label}</span>
                </div>
                """

            # Light Level (interpreted, if available)
            if 'light' in sensors and sensors['light'] is not None:
                light_label = interpret_light(sensors['light'])
                html += f"""
                <div class="sensor-row">
                    <span class="sensor-label">Light Level</span>
                    <span class="sensor-value">{light_label}</span>
                </div>
                """

            html += "</div>"
    else:
        html += '<div class="no-data">Waiting for sensor data...</div>'

    html += """
        </div>
    </body>
    </html>
    """
    return html

@app.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400

        data['received_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        device_name = data.get('device_name', 'Unknown Device')
        latest_readings[device_name] = data

        # Log to file
        with open(DATA_LOG_FILE, 'a') as f:
            f.write(json.dumps(data) + '\n')

        # Console output
        sensors = data.get('sensors', {})
        print(f"\n[{data['received_at']}] {device_name}")
        if 'temperature' in sensors:
            print(f"  Temp: {sensors['temperature']}°C")
        if 'humidity' in sensors:
            print(f"  Humidity: {sensors['humidity']}%")
        if 'audio_peak' in sensors:
            print(f"  Audio: {interpret_audio(sensors['audio_peak'])}")
        if 'light' in sensors:
            print(f"  Light: {interpret_light(sensors['light'])}")

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/latest', methods=['GET'])
def get_latest_data():
    return jsonify(latest_readings), 200

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  HomePOD Server v2")
    print("  Dynamic Display + Interpreted Levels")
    print("="*50)
    print("\nAccess dashboard at: http://<your-pi-ip>:5000")
    print("Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
