#!/usr/bin/env python3
"""
HomePOD Sensor Server v2 - Touch-Friendly Dashboard
- Groups multiple nodes into logical rooms
- Interprets raw sensor values into human-readable levels
- Touch-friendly UI with weather integration
- Optimized for 7-inch HDMI display
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import requests
import time
import os
import uuid

app = Flask(__name__)

DATA_LOG_FILE = "sensor_data_v2.log"
TODO_FILE = "todo_data.json"
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
# WEATHER CONFIGURATION
# ============================================
WEATHER_API_KEY = "f8750f0d79a614efa7c0bb4a4272c311"
WEATHER_CITY = "Calgary"
WEATHER_COUNTRY = "CA"
WEATHER_UNITS = "metric"  # Use "imperial" for Fahrenheit

# Weather cache (refresh every 10 minutes)
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
    """Map OpenWeatherMap icon codes to emoji"""
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
    """Fetch current weather and forecast from OpenWeatherMap"""
    global weather_cache
    
    now = time.time()
    if weather_cache['data'] and (now - weather_cache['last_update']) < WEATHER_CACHE_DURATION:
        return weather_cache['data'], weather_cache['forecast']
    
    try:
        # Current weather
        current_url = f"https://api.openweathermap.org/data/2.5/weather?q={WEATHER_CITY},{WEATHER_COUNTRY}&appid={WEATHER_API_KEY}&units={WEATHER_UNITS}"
        current_resp = requests.get(current_url, timeout=10)
        current_data = current_resp.json()
        
        # 5-day forecast
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
        
        /* Detail Page Styles */
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
        
        /* Status indicators */
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
        
        /* Weather details grid */
        .weather-details {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }
        .weather-detail-item {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
        }
        .weather-detail-item .label {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 8px;
        }
        .weather-detail-item .value {
            font-size: 1.5rem;
            color: #fff;
        }
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    """

# ============================================
# WEB ROUTES - Touch-Friendly Dashboard
# ============================================
@app.route('/')
def home():
    current_time = datetime.now()
    time_str = current_time.strftime('%I:%M %p')
    date_str = current_time.strftime('%A, %B %d')
    
    weather_data, _ = fetch_weather()
    rooms = get_room_data()
    
    # Parse weather
    weather_temp = "--"
    weather_icon = "🌡️"
    weather_condition = "Loading..."
    if weather_data and 'main' in weather_data:
        weather_temp = f"{weather_data['main']['temp']:.0f}°"
        weather_icon = get_weather_icon(weather_data['weather'][0]['icon'])
        weather_condition = weather_data['weather'][0]['description'].title()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HomePOD Dashboard</title>
        {get_base_styles()}
        <script>
            setTimeout(() => location.reload(), 10000);
        </script>
    </head>
    <body>
        <div class="header">
            <div class="page-title">🏠 HomePOD</div>
            <div class="time-display">
                <div class="time">{time_str}</div>
                <div>{date_str}</div>
            </div>
        </div>
        
        <div class="grid">
            <!-- Weather Card (smaller) -->
            <a href="/weather" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Weather · {WEATHER_CITY}</div>
                        <div class="card-value">{weather_temp}</div>
                        <div class="card-subtitle">{weather_condition}</div>
                    </div>
                    <div>
                        <span class="card-icon-small">{weather_icon}</span>
                    </div>
                </div>
            </a>
            
            <!-- To-Do Card -->
            <a href="/todo" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">To-Do List</div>
                        <div class="card-value" style="font-size: 1.8rem;">Tasks</div>
                        <div class="card-subtitle">Tap to manage</div>
                    </div>
                    <div>
                        <span class="card-icon-small">📝</span>
                    </div>
                </div>
            </a>
        </div>
        
        <div class="section-title">Rooms</div>
        <div class="grid">
    """
    
    # Room Cards
    for room_name, data in rooms.items():
        sensors = data.get('sensors', {})
        temp = sensors.get('temperature')
        humidity = sensors.get('humidity')
        
        temp_str = f"{temp:.1f}°" if temp else "--"
        humidity_str = f"{humidity:.0f}%" if humidity else ""
        
        # Choose icon based on room name
        room_icon = "🏠"
        if "bed" in room_name.lower():
            room_icon = "🛏️"
        elif "living" in room_name.lower():
            room_icon = "🛋️"
        elif "kitchen" in room_name.lower():
            room_icon = "🍳"
        elif "bath" in room_name.lower():
            room_icon = "🚿"
        
        room_url = f"/room/{room_name.replace(' ', '%20')}"
        
        html += f"""
            <a href="{room_url}" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">{room_name}</div>
                        <div class="card-value">{temp_str}</div>
                        <div class="card-subtitle">{humidity_str} humidity</div>
                    </div>
                    <span class="card-icon">{room_icon}</span>
                </div>
            </a>
        """
    
    # If no rooms yet
    if not rooms:
        html += '<div class="no-data"><span class="status-dot"></span>Waiting for sensor data...</div>'
    
    html += """
        </div>
    </body>
    </html>
    """
    return html

@app.route('/weather')
def weather_detail():
    weather_data, forecast_data = fetch_weather()
    
    # Current weather
    temp = "--"
    feels_like = "--"
    condition = "Loading..."
    icon = "🌡️"
    humidity = "--"
    wind = "--"
    
    if weather_data and 'main' in weather_data:
        temp = f"{weather_data['main']['temp']:.0f}°"
        feels_like = f"{weather_data['main']['feels_like']:.0f}°"
        condition = weather_data['weather'][0]['description'].title()
        icon = get_weather_icon(weather_data['weather'][0]['icon'])
        humidity = f"{weather_data['main']['humidity']}%"
        wind = f"{weather_data['wind']['speed']:.0f} km/h"
    
    # Parse forecast (get one per day)
    forecast_html = ""
    if forecast_data and 'list' in forecast_data:
        days_seen = set()
        for item in forecast_data['list']:
            dt = datetime.fromtimestamp(item['dt'])
            day_name = dt.strftime('%a')
            if day_name not in days_seen and len(days_seen) < 5:
                days_seen.add(day_name)
                day_icon = get_weather_icon(item['weather'][0]['icon'])
                day_temp = f"{item['main']['temp_max']:.0f}°"
                day_low = f"{item['main']['temp_min']:.0f}°"
                forecast_html += f"""
                    <div class="forecast-day">
                        <div class="day">{day_name}</div>
                        <div class="icon">{day_icon}</div>
                        <div class="temps">
                            <span class="high">{day_temp}</span>
                            <span class="low">{day_low}</span>
                        </div>
                    </div>
                """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Weather - HomePOD</title>
        {get_base_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">Weather</div>
            <div class="time-display">{WEATHER_CITY}</div>
        </div>
        
        <div class="detail-card">
            <div class="big-icon">{icon}</div>
            <div class="big-temp">{temp}</div>
            <div class="condition">{condition}</div>
            
            <div class="weather-details">
                <div class="weather-detail-item">
                    <div class="label">Feels Like</div>
                    <div class="value">{feels_like}</div>
                </div>
                <div class="weather-detail-item">
                    <div class="label">Humidity</div>
                    <div class="value">{humidity}</div>
                </div>
                <div class="weather-detail-item">
                    <div class="label">Wind</div>
                    <div class="value">{wind}</div>
                </div>
                <div class="weather-detail-item">
                    <div class="label">Location</div>
                    <div class="value">{WEATHER_CITY}</div>
                </div>
            </div>
        </div>
        
        <div class="detail-card">
            <div class="card-title" style="margin-bottom: 16px;">5-Day Forecast</div>
            <div class="forecast-row">
                {forecast_html}
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/room/<room_name>')
def room_detail(room_name):
    from urllib.parse import unquote
    room_name = unquote(room_name)
    
    rooms = get_room_data()
    room_data = rooms.get(room_name)
    
    if not room_data:
        sensors_html = '<div class="no-data">No sensor data available for this room</div>'
        temp_display = "--"
    else:
        sensors = room_data.get('sensors', {})
        timestamp = room_data.get('received_at', 'Unknown')
        
        temp = sensors.get('temperature')
        temp_display = f"{temp:.1f}°" if temp else "--"
        
        sensors_html = f'<div class="card-subtitle" style="margin-bottom: 20px;">Last updated: {timestamp}</div>'
        sensors_html += '<div class="sensor-grid">'
        
        if 'temperature' in sensors and sensors['temperature'] is not None:
            sensors_html += f"""
                <div class="sensor-item">
                    <div class="sensor-label">Temperature</div>
                    <div class="sensor-value">{sensors['temperature']:.1f}°C</div>
                </div>
            """
        
        if 'humidity' in sensors and sensors['humidity'] is not None:
            sensors_html += f"""
                <div class="sensor-item">
                    <div class="sensor-label">Humidity</div>
                    <div class="sensor-value">{sensors['humidity']:.1f}%</div>
                </div>
            """
        
        if 'audio_peak' in sensors and sensors['audio_peak'] is not None:
            audio_label = interpret_audio(sensors['audio_peak'])
            sensors_html += f"""
                <div class="sensor-item">
                    <div class="sensor-label">Audio Level</div>
                    <div class="sensor-value">{audio_label}</div>
                </div>
            """
        
        if 'light' in sensors and sensors['light'] is not None:
            light_label = interpret_light(sensors['light'])
            sensors_html += f"""
                <div class="sensor-item">
                    <div class="sensor-label">Light Level</div>
                    <div class="sensor-value">{light_label}</div>
                </div>
            """
        
        sensors_html += '</div>'
    
    # Room icon
    room_icon = "🏠"
    if "bed" in room_name.lower():
        room_icon = "🛏️"
    elif "living" in room_name.lower():
        room_icon = "🛋️"
    elif "kitchen" in room_name.lower():
        room_icon = "🍳"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{room_name} - HomePOD</title>
        {get_base_styles()}
        <script>
            setTimeout(() => location.reload(), 10000);
        </script>
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">{room_name}</div>
            <div style="width: 60px;"></div>
        </div>
        
        <div class="detail-card">
            <div class="big-icon">{room_icon}</div>
            <div class="big-temp">{temp_display}</div>
            {sensors_html}
        </div>
    </body>
    </html>
    """
    return html

# ============================================
# API ROUTES
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
    return jsonify(get_room_data()), 200

@app.route('/api/weather', methods=['GET'])
def get_weather_api():
    weather_data, forecast_data = fetch_weather()
    return jsonify({
        'current': weather_data,
        'forecast': forecast_data
    }), 200

# ============================================
# TO-DO LIST ROUTES
# ============================================
@app.route('/todo')
def todo_page():
    global todo_list
    
    # Build todo items HTML
    items_html = ""
    for item in todo_list:
        completed_class = "completed" if item.get('done') else ""
        check_icon = "✓" if item.get('done') else "○"
        items_html += f"""
            <div class="todo-item {completed_class}" data-id="{item['id']}">
                <form method="POST" action="/todo/toggle/{item['id']}" style="display:inline;">
                    <button type="submit" class="todo-check">{check_icon}</button>
                </form>
                <span class="todo-text">{item['text']}</span>
                <form method="POST" action="/todo/delete/{item['id']}" style="display:inline;">
                    <button type="submit" class="todo-delete">✕</button>
                </form>
            </div>
        """
    
    if not todo_list:
        items_html = '<div class="no-data">No tasks yet. Add one above!</div>'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>To-Do - HomePOD</title>
        {get_base_styles()}
        <style>
            .todo-input-container {{
                display: flex;
                gap: 12px;
                margin-bottom: 24px;
            }}
            .todo-input {{
                flex: 1;
                padding: 16px 20px;
                font-size: 1.1rem;
                border: none;
                border-radius: 16px;
                background: rgba(255,255,255,0.1);
                color: #fff;
                outline: none;
            }}
            .todo-input::placeholder {{
                color: #666;
            }}
            .todo-add-btn {{
                padding: 16px 28px;
                font-size: 1.1rem;
                border: none;
                border-radius: 16px;
                background: linear-gradient(135deg, #00d9ff, #00ff88);
                color: #000;
                font-weight: 600;
                cursor: pointer;
            }}
            .todo-add-btn:active {{
                transform: scale(0.95);
            }}
            .todo-item {{
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 20px;
                background: rgba(255,255,255,0.05);
                border-radius: 16px;
                margin-bottom: 12px;
                transition: all 0.2s;
            }}
            .todo-item.completed {{
                opacity: 0.5;
            }}
            .todo-item.completed .todo-text {{
                text-decoration: line-through;
            }}
            .todo-check {{
                width: 44px;
                height: 44px;
                border: 2px solid #00d9ff;
                border-radius: 50%;
                background: transparent;
                color: #00ff88;
                font-size: 1.4rem;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .todo-check:active {{
                background: rgba(0,217,255,0.3);
            }}
            .todo-text {{
                flex: 1;
                font-size: 1.2rem;
                color: #fff;
            }}
            .todo-delete {{
                width: 44px;
                height: 44px;
                border: none;
                border-radius: 50%;
                background: rgba(255,100,100,0.2);
                color: #ff6464;
                font-size: 1.2rem;
                cursor: pointer;
            }}
            .todo-delete:active {{
                background: rgba(255,100,100,0.4);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/" class="back-btn">←</a>
            <div class="page-title">📝 To-Do List</div>
            <div style="width: 60px;"></div>
        </div>
        
        <div class="detail-card">
            <form method="POST" action="/todo/add" class="todo-input-container">
                <input type="text" name="text" class="todo-input" placeholder="Add a new task..." autocomplete="off" required>
                <button type="submit" class="todo-add-btn">Add</button>
            </form>
            
            {items_html}
        </div>
    </body>
    </html>
    """
    return html

@app.route('/todo/add', methods=['POST'])
def todo_add():
    global todo_list
    text = request.form.get('text', '').strip()
    if text:
        todo_list.append({
            'id': str(uuid.uuid4())[:8],
            'text': text,
            'done': False
        })
        save_todos(todo_list)
    return '<script>window.location.href="/todo";</script>'

@app.route('/todo/toggle/<item_id>', methods=['POST'])
def todo_toggle(item_id):
    global todo_list
    for item in todo_list:
        if item['id'] == item_id:
            item['done'] = not item['done']
            break
    save_todos(todo_list)
    return '<script>window.location.href="/todo";</script>'

@app.route('/todo/delete/<item_id>', methods=['POST'])
def todo_delete(item_id):
    global todo_list
    todo_list = [item for item in todo_list if item['id'] != item_id]
    save_todos(todo_list)
    return '<script>window.location.href="/todo";</script>'


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  HomePOD Server v2 - Touch-Friendly Dashboard")
    print("  Weather: Calgary, AB")
    print("="*50)
    print("\nRoom Configuration:")
    for room, devices in ROOM_CONFIG.items():
        print(f"  {room}: {', '.join(devices)}")
    print("\nAccess dashboard at: http://<your-pi-ip>:5000")
    print("Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
