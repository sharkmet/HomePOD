#!/usr/bin/env python3
"""
HomePOD Sensor Server v3 - Enhanced Multi-App Dashboard
- Weather: Current conditions + 5-day forecast
- To-Do List: Task management with persistence
- Timers: Multiple countdown timers
- Notes: Quick notes and reminders
- Music Player: Control music playback
- System Stats: Raspberry Pi monitoring
- Touch-friendly UI optimized for 7-inch displays
"""

from flask import Flask, request, jsonify, redirect
from datetime import datetime
import json
import requests
import time
import os
import uuid
import subprocess
import platform

app = Flask(__name__)

DATA_LOG_FILE = "sensor_data_v3.log"
TODO_FILE = "todo_data.json"
NOTES_FILE = "notes_data.json"
TIMERS_FILE = "timers_data.json"
MUSIC_FILE = "music_queue.json"
latest_readings = {}

# ============================================
# TO-DO LIST STORAGE
# ============================================
def load_todos():
    if os.path.exists(TODO_FILE):
        try:
            with open(TODO_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_todos(todos):
    with open(TODO_FILE, 'w') as f:
        json.dump(todos, f)

todo_list = load_todos()

# ============================================
# NOTES STORAGE
# ============================================
def load_notes():
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_notes(notes):
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f)

notes_list = load_notes()

# ============================================
# TIMERS STORAGE
# ============================================
def load_timers():
    if os.path.exists(TIMERS_FILE):
        try:
            with open(TIMERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_timers(timers):
    with open(TIMERS_FILE, 'w') as f:
        json.dump(timers, f)

timers_list = load_timers()

# ============================================
# MUSIC QUEUE STORAGE
# ============================================
def load_music_queue():
    if os.path.exists(MUSIC_FILE):
        try:
            with open(MUSIC_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'queue': [], 'current_index': 0, 'is_playing': False}
    return {'queue': [], 'current_index': 0, 'is_playing': False}

def save_music_queue(music_data):
    with open(MUSIC_FILE, 'w') as f:
        json.dump(music_data, f)

music_queue = load_music_queue()

# ============================================
# SYSTEM STATS FUNCTIONS
# ============================================
def get_cpu_temp():
    """Get CPU temperature (works on Raspberry Pi)"""
    try:
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
    except:
        pass
    return None

def get_cpu_usage():
    """Get CPU usage percentage"""
    try:
        if platform.system() == 'Linux':
            result = subprocess.run(['top', '-bn1'], capture_output=True, text=True, timeout=2)
            for line in result.stdout.split('\n'):
                if 'Cpu(s)' in line:
                    parts = line.split(',')
                    idle = float(parts[3].split()[0])
                    return round(100 - idle, 1)
        return None
    except:
        return None

def get_memory_usage():
    """Get memory usage"""
    try:
        if platform.system() == 'Linux':
            result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                total = int(parts[1])
                used = int(parts[2])
                percent = round((used / total) * 100, 1)
                return {'used': used, 'total': total, 'percent': percent}
        return None
    except:
        return None

def get_disk_usage():
    """Get disk usage"""
    try:
        if platform.system() == 'Linux':
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                return {
                    'total': parts[1],
                    'used': parts[2],
                    'percent': parts[4].replace('%', '')
                }
        return None
    except:
        return None

def get_uptime():
    """Get system uptime"""
    try:
        if platform.system() == 'Linux':
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                mins = int((uptime_seconds % 3600) // 60)
                return f"{days}d {hours}h {mins}m"
        return None
    except:
        return None

# ============================================
# WEATHER CONFIGURATION
# ============================================
WEATHER_API_KEY = "f8750f0d79a614efa7c0bb4a4272c311"
WEATHER_CITY = "Calgary"
WEATHER_COUNTRY = "CA"
WEATHER_UNITS = "metric"

weather_cache = {
    'data': None,
    'forecast': None,
    'last_update': 0
}
WEATHER_CACHE_DURATION = 600  # 10 minutes

# ============================================
# ROOM CONFIGURATION
# ============================================
ROOM_CONFIG = {
    "Bedroom": ["HomePOD_Env_Node", "HomePOD_Light_Node"],
    "Living Room": ["HomePOD_Env_Node_2"],
}

# ============================================
# SENSOR INTERPRETATION FUNCTIONS
# ============================================
def interpret_audio(audio_peak):
    if audio_peak is None:
        return None
    if audio_peak <= 50:
        return "Quiet"
    elif audio_peak <= 500:
        return "Talking"
    else:
        return "Loud"

def interpret_light(lux):
    if lux is None:
        return None
    if lux < 50:
        return "Dark"
    elif lux <= 500:
        return "Bright"
    else:
        return "Very Bright"

def get_room_data():
    rooms = {}
    for room_name, device_list in ROOM_CONFIG.items():
        merged_sensors = {}
        latest_timestamp = None
        for device_name in device_list:
            if device_name in latest_readings:
                device_data = latest_readings[device_name]
                sensors = device_data.get('sensors', {})
                timestamp = device_data.get('received_at')
                for key, value in sensors.items():
                    if value is not None:
                        merged_sensors[key] = value
                if timestamp:
                    if latest_timestamp is None or timestamp > latest_timestamp:
                        latest_timestamp = timestamp
        if merged_sensors:
            rooms[room_name] = {
                'sensors': merged_sensors,
                'received_at': latest_timestamp
            }
    return rooms

# ============================================
# WEATHER FUNCTIONS
# ============================================
def get_weather_icon(icon_code):
    icons = {
        '01d': '☀️', '01n': '🌙',
        '02d': '⛅', '02n': '☁️',
        '03d': '☁️', '03n': '☁️',
        '04d': '☁️', '04n': '☁️',
        '09d': '🌧️', '09n': '🌧️',
        '10d': '🌦️', '10n': '🌧️',
        '11d': '⛈️', '11n': '⛈️',
        '13d': '❄️', '13n': '❄️',
        '50d': '🌫️', '50n': '🌫️',
    }
    return icons.get(icon_code, '🌡️')

def fetch_weather():
    global weather_cache

    now = time.time()
    if weather_cache['data'] and (now - weather_cache['last_update']) < WEATHER_CACHE_DURATION:
        return weather_cache['data'], weather_cache['forecast']

    try:
        current_url = f"https://api.openweathermap.org/data/2.5/weather?q={WEATHER_CITY},{WEATHER_COUNTRY}&appid={WEATHER_API_KEY}&units={WEATHER_UNITS}"
        current_resp = requests.get(current_url, timeout=10)
        current_data = current_resp.json()

        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={WEATHER_CITY},{WEATHER_COUNTRY}&appid={WEATHER_API_KEY}&units={WEATHER_UNITS}"
        forecast_resp = requests.get(forecast_url, timeout=10)
        forecast_data = forecast_resp.json()

        weather_cache['data'] = current_data
        weather_cache['forecast'] = forecast_data
        weather_cache['last_update'] = now

        return current_data, forecast_data
    except Exception as e:
        print(f"Weather API error: {e}")
        return weather_cache['data'], weather_cache['forecast']

# ============================================
# SHARED CSS STYLES
# ============================================
def get_base_styles():
    return """
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html { font-size: 18px; }
        body {
            font-family: 'Segoe UI', -apple-system, Arial, sans-serif, 'Noto Color Emoji';
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            color: #eee;
            padding: 20px;
            -webkit-tap-highlight-color: rgba(0,217,255,0.3);
            user-select: none;
            -webkit-user-select: none;
        }
        .section-title {
            font-size: 1rem;
            color: #888;
            margin: 24px 0 12px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .card-icon-small {
            font-size: 1.8rem;
        }

        /* Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding: 0 10px;
        }
        .back-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 60px;
            height: 60px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 16px;
            color: #00d9ff;
            font-size: 1.5rem;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s;
        }
        .back-btn:active {
            background: rgba(0,217,255,0.3);
            transform: scale(0.95);
        }
        .page-title {
            font-size: 1.8rem;
            font-weight: 600;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .time-display {
            text-align: right;
            color: #888;
            font-size: 0.9rem;
        }
        .time-display .time {
            font-size: 1.4rem;
            color: #fff;
            font-weight: 300;
        }

        /* Card Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Tappable Cards */
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 24px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.15s ease;
            cursor: pointer;
            min-height: 140px;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .card:active {
            transform: scale(0.97);
            background: rgba(0,217,255,0.15);
            border-color: rgba(0,217,255,0.4);
        }
        .card.large {
            grid-column: span 2;
        }
        @media (max-width: 600px) {
            .card.large { grid-column: span 1; }
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }
        .card-icon {
            font-size: 2.5rem;
        }
        .card-title {
            font-size: 1.1rem;
            color: #888;
            margin-bottom: 4px;
        }
        .card-value {
            font-size: 2.8rem;
            font-weight: 300;
            color: #fff;
        }
        .card-subtitle {
            font-size: 0.85rem;
            color: #666;
            margin-top: 8px;
        }
        .card-arrow {
            color: #00d9ff;
            font-size: 1.5rem;
            opacity: 0.6;
        }

        /* Sensor Rows */
        .sensor-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-top: 16px;
        }
        .sensor-item {
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .sensor-label {
            font-size: 0.8rem;
            color: #888;
            margin-bottom: 6px;
        }
        .sensor-value {
            font-size: 1.4rem;
            font-weight: 500;
            color: #00ff88;
        }

        /* Detail Card */
        .detail-card {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
        }
        .big-temp {
            font-size: 5rem;
            font-weight: 200;
            color: #fff;
            text-align: center;
        }
        .big-icon {
            font-size: 4rem;
            text-align: center;
            margin-bottom: 10px;
        }
        .condition {
            text-align: center;
            font-size: 1.3rem;
            color: #888;
            margin-bottom: 30px;
        }

        /* Forecast */
        .forecast-row {
            display: flex;
            justify-content: space-between;
            overflow-x: auto;
            gap: 12px;
            padding: 10px 0;
        }
        .forecast-day {
            flex: 0 0 auto;
            text-align: center;
            padding: 16px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            min-width: 90px;
        }
        .forecast-day .day {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 8px;
        }
        .forecast-day .icon {
            font-size: 1.8rem;
            margin-bottom: 8px;
        }
        .forecast-day .temps {
            font-size: 0.9rem;
        }
        .forecast-day .high { color: #fff; }
        .forecast-day .low { color: #666; margin-left: 6px; }

        /* Status */
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

        .no-data {
            text-align: center;
            padding: 60px;
            color: #666;
            font-size: 1.2rem;
        }

        /* To-Do & Notes Lists */
        .item-list {
            margin-top: 20px;
        }
        .item {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }
        .item-text {
            flex: 1;
            font-size: 1.1rem;
            word-break: break-word;
        }
        .item.completed .item-text {
            text-decoration: line-through;
            opacity: 0.5;
        }
        .item-actions {
            display: flex;
            gap: 8px;
            flex-shrink: 0;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        .btn-primary {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #000;
            font-weight: 600;
        }
        .btn-primary:active {
            transform: scale(0.95);
        }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        .btn-secondary:active {
            background: rgba(255,255,255,0.2);
            transform: scale(0.95);
        }
        .btn-icon {
            width: 48px;
            height: 48px;
            padding: 0;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .btn-large {
            width: 80px;
            height: 80px;
            font-size: 2rem;
        }

        /* Forms */
        .input-group {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }
        .input, .textarea {
            flex: 1;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 1rem;
            font-family: inherit;
        }
        .textarea {
            min-height: 120px;
            resize: vertical;
        }
        .input:focus, .textarea:focus {
            outline: none;
            border-color: rgba(0,217,255,0.5);
            background: rgba(255,255,255,0.08);
        }

        /* Timer Display */
        .timer-display {
            font-size: 4rem;
            font-weight: 200;
            text-align: center;
            color: #00d9ff;
            font-variant-numeric: tabular-nums;
            margin: 20px 0;
        }
        .timer-item {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
        }
        .timer-name {
            font-size: 1.2rem;
            margin-bottom: 12px;
            color: #888;
        }
        .timer-time {
            font-size: 2.5rem;
            font-weight: 300;
            margin-bottom: 12px;
            font-variant-numeric: tabular-nums;
        }
        .timer-controls {
            display: flex;
            gap: 8px;
        }
        .timer-running {
            color: #00ff88;
        }
        .timer-finished {
            color: #ff4444;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.3; }
        }

        /* Music Player */
        .now-playing {
            background: rgba(0,217,255,0.1);
            border: 2px solid rgba(0,217,255,0.3);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            text-align: center;
        }
        .album-art {
            font-size: 6rem;
            margin-bottom: 20px;
        }
        .track-title {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .track-artist {
            font-size: 1.2rem;
            color: #888;
            margin-bottom: 20px;
        }
        .playback-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-top: 30px;
        }
        .track-item {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .track-item.playing {
            background: rgba(0,217,255,0.15);
            border: 1px solid rgba(0,217,255,0.3);
        }

        /* Stats Gauges */
        .gauge {
            position: relative;
            text-align: center;
            padding: 20px;
        }
        .gauge-value {
            font-size: 3rem;
            font-weight: 300;
            color: #00ff88;
        }
        .gauge-label {
            font-size: 0.9rem;
            color: #888;
            margin-top: 8px;
        }
        .progress-bar {
            width: 100%;
            height: 12px;
            background: rgba(255,255,255,0.1);
            border-radius: 6px;
            overflow: hidden;
            margin-top: 12px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            transition: width 0.3s;
        }
    </style>
    """

# ============================================
# HOME PAGE
# ============================================
@app.route('/')
def home():
    rooms = get_room_data()
    current_time = datetime.now().strftime('%I:%M %p')
    current_date = datetime.now().strftime('%A, %b %d')

    weather, forecast = fetch_weather()
    weather_temp = weather['main']['temp'] if weather else "N/A"
    weather_desc = weather['weather'][0]['description'].title() if weather else "Loading..."
    weather_icon = get_weather_icon(weather['weather'][0]['icon']) if weather else "🌡️"

    # Room emoji mapping
    room_icons = {
        "Bedroom": "🛏️",
        "Living Room": "🛋️",
        "Kitchen": "🍳",
        "Office": "💼",
        "Bathroom": "🚿"
    }

    # Get current playing track
    current_track = None
    if music_queue['queue'] and music_queue['current_index'] < len(music_queue['queue']):
        current_track = music_queue['queue'][music_queue['current_index']]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HomePOD Dashboard</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <div class="page-title">🏠 HomePOD</div>
            <div class="time-display">
                <div class="time">{current_time}</div>
                <div>{current_date}</div>
            </div>
        </div>

        <div class="section-title">Apps</div>
        <div class="grid">
            <a href="/weather" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Weather</div>
                        <div class="card-value">{weather_temp}°C</div>
                        <div class="card-subtitle">{weather_desc}</div>
                    </div>
                    <div>
                        <div class="card-icon">{weather_icon}</div>
                    </div>
                </div>
            </a>

            <a href="/todo" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">To-Do List</div>
                        <div class="card-value">{len([t for t in todo_list if not t.get('completed')])}</div>
                        <div class="card-subtitle">tasks remaining</div>
                    </div>
                    <div class="card-icon">✅</div>
                </div>
            </a>

            <a href="/timers" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Timers</div>
                        <div class="card-value">{len([t for t in timers_list if t.get('running')])}</div>
                        <div class="card-subtitle">active timers</div>
                    </div>
                    <div class="card-icon">⏱️</div>
                </div>
            </a>

            <a href="/notes" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Notes</div>
                        <div class="card-value">{len(notes_list)}</div>
                        <div class="card-subtitle">saved notes</div>
                    </div>
                    <div class="card-icon">📝</div>
                </div>
            </a>

            <a href="/music" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Music</div>
                        <div class="card-value" style="font-size: 1.5rem;">{'▶️ Playing' if music_queue.get('is_playing') else '⏸️ Paused'}</div>
                        <div class="card-subtitle">{current_track['title'] if current_track else 'No track'}</div>
                    </div>
                    <div class="card-icon">🎵</div>
                </div>
            </a>

            <a href="/system" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">System Stats</div>
                        <div class="card-value" style="font-size: 1.8rem;">{get_cpu_temp() or 'N/A'}°C</div>
                        <div class="card-subtitle">CPU Temperature</div>
                    </div>
                    <div class="card-icon">📊</div>
                </div>
            </a>
        </div>

        <div class="section-title">Rooms</div>
        <div class="grid">
    """

    if not rooms:
        html += '<div class="no-data">⏳ Waiting for sensor data...</div>'
    else:
        for room_name, data in rooms.items():
            sensors = data['sensors']
            room_icon = room_icons.get(room_name, "🏠")
            temp = sensors.get('temperature', 'N/A')
            humidity = sensors.get('humidity', 'N/A')
            light = sensors.get('light')
            audio_peak = sensors.get('audio_peak')

            if isinstance(temp, (int, float)):
                temp = f"{temp:.1f}°C"
            if isinstance(humidity, (int, float)):
                humidity = f"{humidity:.0f}%"

            light_label = interpret_light(light) or "N/A"
            audio_label = interpret_audio(audio_peak) or "N/A"

            html += f"""
            <a href="/room/{room_name}" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">{room_icon} {room_name}</div>
                        <div class="card-value">{temp}</div>
                    </div>
                    <div class="card-arrow">→</div>
                </div>
                <div class="sensor-grid">
                    <div class="sensor-item">
                        <div class="sensor-label">Humidity</div>
                        <div class="sensor-value">{humidity}</div>
                    </div>
                    <div class="sensor-item">
                        <div class="sensor-label">Light</div>
                        <div class="sensor-value">{light_label}</div>
                    </div>
                </div>
            </a>
            """

    html += """
        </div>
        <script>
            setTimeout(() => location.reload(), 10000);
        </script>
    </body>
    </html>
    """
    return html

# ============================================
# WEATHER PAGE (unchanged, keeping for completeness)
# ============================================
@app.route('/weather')
def weather_page():
    current, forecast = fetch_weather()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Weather</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">Weather</div>
            <div style="width: 60px;"></div>
        </div>
    """

    if current:
        temp = current['main']['temp']
        feels_like = current['main']['feels_like']
        description = current['weather'][0]['description'].title()
        icon = get_weather_icon(current['weather'][0]['icon'])
        humidity = current['main']['humidity']
        wind_speed = current['wind']['speed']

        html += f"""
        <div class="detail-card">
            <div class="big-icon">{icon}</div>
            <div class="big-temp">{temp:.0f}°C</div>
            <div class="condition">{description}</div>
            <div class="sensor-grid">
                <div class="sensor-item">
                    <div class="sensor-label">Feels Like</div>
                    <div class="sensor-value">{feels_like:.0f}°C</div>
                </div>
                <div class="sensor-item">
                    <div class="sensor-label">Humidity</div>
                    <div class="sensor-value">{humidity}%</div>
                </div>
                <div class="sensor-item">
                    <div class="sensor-label">Wind Speed</div>
                    <div class="sensor-value">{wind_speed} m/s</div>
                </div>
                <div class="sensor-item">
                    <div class="sensor-label">Location</div>
                    <div class="sensor-value">{WEATHER_CITY}</div>
                </div>
            </div>
        </div>
        """

    if forecast and 'list' in forecast:
        daily_forecasts = {}
        for item in forecast['list']:
            date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
            if date not in daily_forecasts:
                daily_forecasts[date] = {
                    'temps': [],
                    'icon': item['weather'][0]['icon']
                }
            daily_forecasts[date]['temps'].append(item['main']['temp'])

        html += """
        <div class="section-title">5-Day Forecast</div>
        <div class="forecast-row">
        """

        for date, data in list(daily_forecasts.items())[:5]:
            day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%a')
            high = max(data['temps'])
            low = min(data['temps'])
            icon = get_weather_icon(data['icon'])

            html += f"""
            <div class="forecast-day">
                <div class="day">{day_name}</div>
                <div class="icon">{icon}</div>
                <div class="temps">
                    <span class="high">{high:.0f}°</span>
                    <span class="low">{low:.0f}°</span>
                </div>
            </div>
            """

        html += "</div>"

    html += """
        <script>
            setTimeout(() => location.reload(), 10000);
        </script>
    </body>
    </html>
    """
    return html

# ============================================
# ROOM DETAIL PAGE (unchanged)
# ============================================
@app.route('/room/<room_name>')
def room_detail(room_name):
    rooms = get_room_data()
    room_data = rooms.get(room_name)

    if not room_data:
        return redirect('/')

    sensors = room_data['sensors']
    timestamp = room_data.get('received_at', 'Unknown')

    room_icons = {
        "Bedroom": "🛏️",
        "Living Room": "🛋️",
        "Kitchen": "🍳",
        "Office": "💼",
        "Bathroom": "🚿"
    }
    room_icon = room_icons.get(room_name, "🏠")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{room_name}</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">{room_icon} {room_name}</div>
            <div style="width: 60px;"></div>
        </div>

        <div class="detail-card">
            <div class="section-title">Temperature & Humidity</div>
            <div class="sensor-grid">
    """

    temp = sensors.get('temperature')
    humidity = sensors.get('humidity')
    light = sensors.get('light')
    audio_level = sensors.get('audio_level')
    audio_peak = sensors.get('audio_peak')

    if temp is not None:
        html += f"""
        <div class="sensor-item">
            <div class="sensor-label">🌡️ Temperature</div>
            <div class="sensor-value">{temp:.1f}°C</div>
        </div>
        """

    if humidity is not None:
        html += f"""
        <div class="sensor-item">
            <div class="sensor-label">💧 Humidity</div>
            <div class="sensor-value">{humidity:.0f}%</div>
        </div>
        """

    if light is not None:
        light_label = interpret_light(light)
        html += f"""
        <div class="sensor-item">
            <div class="sensor-label">💡 Light</div>
            <div class="sensor-value">{light_label}</div>
            <div class="card-subtitle">{light:.0f} lux</div>
        </div>
        """

    if audio_peak is not None:
        audio_label = interpret_audio(audio_peak)
        html += f"""
        <div class="sensor-item">
            <div class="sensor-label">🔊 Sound</div>
            <div class="sensor-value">{audio_label}</div>
            <div class="card-subtitle">Peak: {audio_peak}</div>
        </div>
        """

    html += f"""
            </div>
            <div class="card-subtitle" style="margin-top: 20px; text-align: center;">
                <span class="status-dot"></span>
                Last updated: {timestamp}
            </div>
        </div>

        <script>
            setTimeout(() => location.reload(), 10000);
        </script>
    </body>
    </html>
    """
    return html

# ============================================
# TO-DO LIST PAGE (unchanged)
# ============================================
@app.route('/todo')
def todo_page():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>To-Do List</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">✅ To-Do List</div>
            <div style="width: 60px;"></div>
        </div>

        <div class="detail-card">
            <form action="/todo/add" method="POST" class="input-group">
                <input type="text" name="text" class="input" placeholder="Add a new task..." required>
                <button type="submit" class="btn btn-primary">Add</button>
            </form>
        </div>

        <div class="item-list">
    """

    if not todo_list:
        html += '<div class="no-data">📝 No tasks yet. Add one above!</div>'
    else:
        for item in todo_list:
            item_id = item['id']
            text = item['text']
            completed = item.get('completed', False)
            completed_class = 'completed' if completed else ''

            html += f"""
            <div class="item {completed_class}">
                <div class="item-text">{text}</div>
                <div class="item-actions">
                    <form action="/todo/toggle/{item_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-icon btn-secondary">
                            {'✓' if not completed else '↩'}
                        </button>
                    </form>
                    <form action="/todo/delete/{item_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-icon btn-secondary">🗑️</button>
                    </form>
                </div>
            </div>
            """

    html += """
        </div>
    </body>
    </html>
    """
    return html

@app.route('/todo/add', methods=['POST'])
def todo_add():
    text = request.form.get('text', '').strip()
    if text:
        todo_list.append({
            'id': str(uuid.uuid4()),
            'text': text,
            'completed': False
        })
        save_todos(todo_list)
    return redirect('/todo')

@app.route('/todo/toggle/<item_id>', methods=['POST'])
def todo_toggle(item_id):
    for item in todo_list:
        if item['id'] == item_id:
            item['completed'] = not item.get('completed', False)
            break
    save_todos(todo_list)
    return redirect('/todo')

@app.route('/todo/delete/<item_id>', methods=['POST'])
def todo_delete(item_id):
    global todo_list
    todo_list = [item for item in todo_list if item['id'] != item_id]
    save_todos(todo_list)
    return redirect('/todo')

# ============================================
# TIMERS PAGE (unchanged)
# ============================================
@app.route('/timers')
def timers_page():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Timers</title>
        {get_base_styles()}
        <script>
            function formatTime(seconds) {{
                const hours = Math.floor(seconds / 3600);
                const mins = Math.floor((seconds % 3600) / 60);
                const secs = seconds % 60;
                if (hours > 0) {{
                    return hours + ':' + String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
                }}
                return mins + ':' + String(secs).padStart(2, '0');
            }}

            function updateTimers() {{
                const timers = {json.dumps(timers_list)};
                const now = Date.now() / 1000;

                timers.forEach((timer, index) => {{
                    if (!timer.running) return;

                    const elapsed = now - timer.start_time;
                    const remaining = Math.max(0, timer.duration - elapsed);

                    const elem = document.getElementById('timer-' + index);
                    if (elem) {{
                        elem.textContent = formatTime(Math.floor(remaining));
                        if (remaining <= 0) {{
                            elem.classList.add('timer-finished');
                            if ('vibrate' in navigator) navigator.vibrate(200);
                        }} else {{
                            elem.classList.remove('timer-finished');
                        }}
                    }}
                }});
            }}

            setInterval(updateTimers, 1000);
            setTimeout(updateTimers, 100);
        </script>
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">⏱️ Timers</div>
            <div style="width: 60px;"></div>
        </div>

        <div class="detail-card">
            <form action="/timers/add" method="POST">
                <div class="input-group">
                    <input type="text" name="name" class="input" placeholder="Timer name (e.g., Pizza)" required>
                </div>
                <div class="input-group">
                    <input type="number" name="minutes" class="input" placeholder="Minutes" min="0" max="999" value="5" required>
                    <input type="number" name="seconds" class="input" placeholder="Seconds" min="0" max="59" value="0">
                    <button type="submit" class="btn btn-primary">Create</button>
                </div>
            </form>
        </div>

        <div class="item-list">
    """

    if not timers_list:
        html += '<div class="no-data">⏱️ No timers yet. Create one above!</div>'
    else:
        for index, timer in enumerate(timers_list):
            timer_id = timer['id']
            name = timer['name']
            duration = timer['duration']
            running = timer.get('running', False)

            status_class = 'timer-running' if running else ''

            html += f"""
            <div class="timer-item">
                <div class="timer-name">{name}</div>
                <div class="timer-time {status_class}" id="timer-{index}">
                    {duration // 60}:{duration % 60:02d}
                </div>
                <div class="timer-controls">
            """

            if not running:
                html += f"""
                <form action="/timers/start/{timer_id}" method="POST" style="display:inline; flex:1;">
                    <button type="submit" class="btn btn-primary" style="width:100%;">▶ Start</button>
                </form>
                """
            else:
                html += f"""
                <form action="/timers/stop/{timer_id}" method="POST" style="display:inline; flex:1;">
                    <button type="submit" class="btn btn-secondary" style="width:100%;">⏸ Stop</button>
                </form>
                """

            html += f"""
                <form action="/timers/delete/{timer_id}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-icon btn-secondary">🗑️</button>
                </form>
                </div>
            </div>
            """

    html += """
        </div>
    </body>
    </html>
    """
    return html

@app.route('/timers/add', methods=['POST'])
def timers_add():
    name = request.form.get('name', '').strip()
    minutes = int(request.form.get('minutes', 0))
    seconds = int(request.form.get('seconds', 0))

    if name and (minutes > 0 or seconds > 0):
        duration = minutes * 60 + seconds
        timers_list.append({
            'id': str(uuid.uuid4()),
            'name': name,
            'duration': duration,
            'running': False,
            'start_time': 0
        })
        save_timers(timers_list)
    return redirect('/timers')

@app.route('/timers/start/<timer_id>', methods=['POST'])
def timers_start(timer_id):
    for timer in timers_list:
        if timer['id'] == timer_id:
            timer['running'] = True
            timer['start_time'] = time.time()
            break
    save_timers(timers_list)
    return redirect('/timers')

@app.route('/timers/stop/<timer_id>', methods=['POST'])
def timers_stop(timer_id):
    for timer in timers_list:
        if timer['id'] == timer_id:
            timer['running'] = False
            break
    save_timers(timers_list)
    return redirect('/timers')

@app.route('/timers/delete/<timer_id>', methods=['POST'])
def timers_delete(timer_id):
    global timers_list
    timers_list = [t for t in timers_list if t['id'] != timer_id]
    save_timers(timers_list)
    return redirect('/timers')

# ============================================
# NOTES PAGE (unchanged)
# ============================================
@app.route('/notes')
def notes_page():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Notes</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">📝 Notes</div>
            <div style="width: 60px;"></div>
        </div>

        <div class="detail-card">
            <form action="/notes/add" method="POST">
                <input type="text" name="title" class="input" placeholder="Note title..." required style="margin-bottom: 12px;">
                <textarea name="content" class="textarea" placeholder="Write your note here..." required></textarea>
                <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 12px;">Save Note</button>
            </form>
        </div>

        <div class="item-list">
    """

    if not notes_list:
        html += '<div class="no-data">📝 No notes yet. Create one above!</div>'
    else:
        for note in reversed(notes_list):
            note_id = note['id']
            title = note['title']
            content = note['content']
            timestamp = note.get('created', 'Unknown')

            preview = content[:100] + '...' if len(content) > 100 else content

            html += f"""
            <div class="item">
                <div style="flex: 1;">
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 8px;">{title}</div>
                    <div style="color: #888; margin-bottom: 8px; white-space: pre-wrap;">{preview}</div>
                    <div style="font-size: 0.8rem; color: #666;">{timestamp}</div>
                </div>
                <div class="item-actions">
                    <a href="/notes/view/{note_id}" class="btn btn-icon btn-secondary">👁️</a>
                    <form action="/notes/delete/{note_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-icon btn-secondary">🗑️</button>
                    </form>
                </div>
            </div>
            """

    html += """
        </div>
    </body>
    </html>
    """
    return html

@app.route('/notes/add', methods=['POST'])
def notes_add():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if title and content:
        notes_list.append({
            'id': str(uuid.uuid4()),
            'title': title,
            'content': content,
            'created': datetime.now().strftime('%Y-%m-%d %I:%M %p')
        })
        save_notes(notes_list)
    return redirect('/notes')

@app.route('/notes/view/<note_id>')
def notes_view(note_id):
    note = None
    for n in notes_list:
        if n['id'] == note_id:
            note = n
            break

    if not note:
        return redirect('/notes')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{note['title']}</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/notes" class="back-btn">←</a>
            <div class="page-title">📝 {note['title']}</div>
            <div style="width: 60px;"></div>
        </div>

        <div class="detail-card">
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 20px;">
                Created: {note.get('created', 'Unknown')}
            </div>
            <div style="white-space: pre-wrap; font-size: 1.1rem; line-height: 1.6;">
                {note['content']}
            </div>
        </div>

        <div style="margin-top: 20px;">
            <form action="/notes/delete/{note_id}" method="POST">
                <button type="submit" class="btn btn-secondary" style="width: 100%;">🗑️ Delete Note</button>
            </form>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/notes/delete/<note_id>', methods=['POST'])
def notes_delete(note_id):
    global notes_list
    notes_list = [n for n in notes_list if n['id'] != note_id]
    save_notes(notes_list)
    return redirect('/notes')

# ============================================
# MUSIC PLAYER PAGE
# ============================================
@app.route('/music')
def music_page():
    current_track = None
    current_index = music_queue.get('current_index', 0)
    is_playing = music_queue.get('is_playing', False)

    if music_queue['queue'] and current_index < len(music_queue['queue']):
        current_track = music_queue['queue'][current_index]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Music Player</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">🎵 Music Player</div>
            <div style="width: 60px;"></div>
        </div>

        <div class="now-playing">
            <div class="album-art">{'🎵' if current_track else '🎶'}</div>
            <div class="track-title">{current_track['title'] if current_track else 'No Track Playing'}</div>
            <div class="track-artist">{current_track['artist'] if current_track else 'Add songs to queue'}</div>

            <div class="playback-controls">
                <form action="/music/previous" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-icon btn-large btn-secondary">⏮</button>
                </form>
                <form action="/music/{'pause' if is_playing else 'play'}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-icon btn-large btn-primary">{'⏸️' if is_playing else '▶️'}</button>
                </form>
                <form action="/music/next" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-icon btn-large btn-secondary">⏭</button>
                </form>
            </div>
        </div>

        <div class="detail-card">
            <form action="/music/add" method="POST">
                <div class="input-group">
                    <input type="text" name="title" class="input" placeholder="Song title..." required>
                </div>
                <div class="input-group">
                    <input type="text" name="artist" class="input" placeholder="Artist name..." required>
                    <button type="submit" class="btn btn-primary">Add to Queue</button>
                </div>
            </form>
        </div>

        <div class="section-title">Queue ({len(music_queue['queue'])} songs)</div>
        <div class="item-list">
    """

    if not music_queue['queue']:
        html += '<div class="no-data">🎵 Queue is empty. Add songs above!</div>'
    else:
        for index, track in enumerate(music_queue['queue']):
            track_id = track['id']
            is_current = (index == current_index)
            current_class = 'playing' if is_current else ''

            html += f"""
            <div class="track-item {current_class}">
                <div style="flex: 1;">
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 4px;">
                        {' ▶️ ' if is_current else ''}{track['title']}
                    </div>
                    <div style="color: #888;">{track['artist']}</div>
                </div>
                <div class="item-actions">
                    <form action="/music/play/{index}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-icon btn-secondary">▶️</button>
                    </form>
                    <form action="/music/remove/{track_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-icon btn-secondary">🗑️</button>
                    </form>
                </div>
            </div>
            """

    html += """
        </div>
    </body>
    </html>
    """
    return html

@app.route('/music/add', methods=['POST'])
def music_add():
    title = request.form.get('title', '').strip()
    artist = request.form.get('artist', '').strip()

    if title and artist:
        music_queue['queue'].append({
            'id': str(uuid.uuid4()),
            'title': title,
            'artist': artist
        })
        save_music_queue(music_queue)
    return redirect('/music')

@app.route('/music/play', methods=['POST'])
def music_play():
    music_queue['is_playing'] = True
    save_music_queue(music_queue)
    return redirect('/music')

@app.route('/music/pause', methods=['POST'])
def music_pause():
    music_queue['is_playing'] = False
    save_music_queue(music_queue)
    return redirect('/music')

@app.route('/music/play/<int:index>', methods=['POST'])
def music_play_index(index):
    if 0 <= index < len(music_queue['queue']):
        music_queue['current_index'] = index
        music_queue['is_playing'] = True
        save_music_queue(music_queue)
    return redirect('/music')

@app.route('/music/next', methods=['POST'])
def music_next():
    if music_queue['queue']:
        music_queue['current_index'] = (music_queue['current_index'] + 1) % len(music_queue['queue'])
        save_music_queue(music_queue)
    return redirect('/music')

@app.route('/music/previous', methods=['POST'])
def music_previous():
    if music_queue['queue']:
        music_queue['current_index'] = (music_queue['current_index'] - 1) % len(music_queue['queue'])
        save_music_queue(music_queue)
    return redirect('/music')

@app.route('/music/remove/<track_id>', methods=['POST'])
def music_remove(track_id):
    music_queue['queue'] = [t for t in music_queue['queue'] if t['id'] != track_id]
    if music_queue['current_index'] >= len(music_queue['queue']) and music_queue['queue']:
        music_queue['current_index'] = len(music_queue['queue']) - 1
    save_music_queue(music_queue)
    return redirect('/music')

# ============================================
# SYSTEM STATS PAGE
# ============================================
@app.route('/system')
def system_page():
    cpu_temp = get_cpu_temp()
    cpu_usage = get_cpu_usage()
    memory = get_memory_usage()
    disk = get_disk_usage()
    uptime = get_uptime()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>System Stats</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">📊 System Stats</div>
            <div style="width: 60px;"></div>
        </div>

        <div class="detail-card">
            <div class="big-icon">💻</div>
            <div style="text-align: center; font-size: 1.3rem; color: #888; margin-bottom: 30px;">
                Raspberry Pi Status
            </div>

            <div class="sensor-grid" style="grid-template-columns: repeat(2, 1fr);">
                <div class="sensor-item">
                    <div class="sensor-label">🌡️ CPU Temp</div>
                    <div class="sensor-value">{cpu_temp if cpu_temp else 'N/A'}°C</div>
                </div>
                <div class="sensor-item">
                    <div class="sensor-label">⚡ CPU Usage</div>
                    <div class="sensor-value">{cpu_usage if cpu_usage else 'N/A'}%</div>
                </div>
            </div>
        </div>

        <div class="detail-card">
            <div class="section-title">Memory Usage</div>
    """

    if memory:
        html += f"""
            <div class="gauge">
                <div class="gauge-value">{memory['percent']}%</div>
                <div class="gauge-label">{memory['used']} MB / {memory['total']} MB</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {memory['percent']}%;"></div>
                </div>
            </div>
        """
    else:
        html += '<div class="no-data">Memory info unavailable</div>'

    html += """
        </div>

        <div class="detail-card">
            <div class="section-title">Disk Usage</div>
    """

    if disk:
        html += f"""
            <div class="gauge">
                <div class="gauge-value">{disk['percent']}%</div>
                <div class="gauge-label">{disk['used']} / {disk['total']}</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {disk['percent']}%;"></div>
                </div>
            </div>
        """
    else:
        html += '<div class="no-data">Disk info unavailable</div>'

    html += f"""
        </div>

        <div class="detail-card">
            <div class="sensor-grid" style="grid-template-columns: 1fr;">
                <div class="sensor-item">
                    <div class="sensor-label">⏱️ Uptime</div>
                    <div class="sensor-value" style="font-size: 1.2rem;">{uptime if uptime else 'N/A'}</div>
                </div>
            </div>
        </div>

        <script>
            setTimeout(() => location.reload(), 5000);
        </script>
    </body>
    </html>
    """
    return html

# ============================================
# SENSOR DATA API
# ============================================
@app.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400

        data['received_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        device_name = data.get('device_name', 'Unknown Device')
        latest_readings[device_name] = data

        with open(DATA_LOG_FILE, 'a') as f:
            f.write(json.dumps(data) + '\n')

        print(f"\n{'='*50}")
        print(f"Received data from: {device_name}")
        print(f"Time: {data['received_at']}")
        if 'sensors' in data:
            sensors = data['sensors']
            print(f"Temperature: {sensors.get('temperature', 'N/A')}°C")
            print(f"Humidity: {sensors.get('humidity', 'N/A')}%")
            print(f"Light: {sensors.get('light', 'N/A')} lux")
            print(f"Audio Level: {sensors.get('audio_level', 'N/A')}")
        print(f"{'='*50}\n")

        return jsonify({'status': 'success', 'device_name': device_name}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/latest', methods=['GET'])
def get_latest():
    return jsonify(latest_readings), 200

@app.route('/api/weather', methods=['GET'])
def api_weather():
    current, forecast = fetch_weather()
    return jsonify({
        'current': current,
        'forecast': forecast
    }), 200

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("   HomePOD Dashboard Server v3")
    print("   Enhanced 6-App Dashboard")
    print("="*60)
    print("\nApps:")
    print("  ☀️  Weather - Current + 5-day forecast")
    print("  ✅ To-Do List - Task management")
    print("  ⏱️  Timers - Multiple countdown timers")
    print("  📝 Notes - Quick notes & reminders")
    print("  🎵 Music Player - Queue & playback control")
    print("  📊 System Stats - Raspberry Pi monitoring")
    print("\nServer Configuration:")
    print(f"  - Port: 5000")
    print(f"  - Data log: {DATA_LOG_FILE}")
    print(f"  - Weather: {WEATHER_CITY}, {WEATHER_COUNTRY}")
    print("\nAccess:")
    print("  - Local: http://localhost:5000")
    print("  - Network: http://<raspberry-pi-ip>:5000")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)
