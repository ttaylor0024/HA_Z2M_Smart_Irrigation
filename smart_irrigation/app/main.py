#!/usr/bin/env python3
"""
Smart Irrigation Controller Add-on
Manages automated irrigation with weather integration
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import aiohttp
from flask import Flask, render_template, request, jsonify
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- History Manager Class ---
class HistoryManager:
    """Manages reading and writing historical data for charting."""
    def __init__(self, history_file: str = "/data/history.json"):
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.history = {}
            for i in range(7):
                day_str = (date.today() - timedelta(days=i)).isoformat()
                self.history[day_str] = {"water_used": 0, "rainfall": 0}
            return self.history

    def _save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=4)

    def log_data(self, key: str, value: float):
        today_str = date.today().isoformat()
        if today_str not in self.history:
            self.history[today_str] = {"water_used": 0, "rainfall": 0}
        self.history[today_str][key] = self.history[today_str].get(key, 0) + value
        self._save_history()

    def set_daily_rainfall(self, rainfall: float):
        today_str = date.today().isoformat()
        if today_str not in self.history:
            self.history[today_str] = {"water_used": 0, "rainfall": 0}
        self.history[today_str]['rainfall'] = rainfall
        self._save_history()

    def get_last_7_days(self) -> Dict:
        labels, water_data, rain_data = [], [], []
        for i in range(6, -1, -1):
            day = date.today() - timedelta(days=i)
            day_str = day.isoformat()
            labels.append(day.strftime('%a'))
            day_data = self.history.get(day_str, {"water_used": 0, "rainfall": 0})
            water_data.append(day_data.get('water_used', 0))
            rain_data.append(day_data.get('rainfall', 0))
        return {"labels": labels, "datasets": [{"label": "Water Used", "data": water_data, "borderColor": "#00a8ff", "backgroundColor": "rgba(0, 168, 255, 0.2)", "fill": True, "yAxisID": "y"}, {"label": "Rainfall", "data": rain_data, "borderColor": "#00c853", "backgroundColor": "rgba(0, 200, 83, 0.2)", "fill": True, "yAxisID": "y1"}]}

# --- WeatherProvider Class ---
class WeatherProvider:
    def __init__(self, provider: str, api_key: str, lat: float, lon: float, units: str = "metric"):
        self.provider, self.api_key, self.lat, self.lon, self.units = provider, api_key, lat, lon, units

    async def get_forecast(self, hours: int) -> Dict:
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {'lat': self.lat, 'lon': self.lon, 'appid': self.api_key, 'units': 'metric'}
        try:
            async with aiohttp.ClientSession() as session, session.get(url, params=params) as response:
                if response.status != 200: return {'status': 'error'}
                data = await response.json()
                total_rain, rain_chance, now = 0.0, 0.0, datetime.now()
                start_time, end_time = (now + timedelta(hours=hours), now) if hours < 0 else (now, now + timedelta(hours=hours))
                for item in data['list']:
                    forecast_time = datetime.fromtimestamp(item['dt'])
                    if start_time <= forecast_time <= end_time:
                        total_rain += item.get('rain', {}).get('3h', 0)
                        rain_chance = max(rain_chance, item.get('pop', 0) * 100)
                if self.units == "imperial": total_rain *= 0.0393701
                return {'rain_mm': total_rain, 'rain_chance': rain_chance, 'status': 'success'}
        except Exception as e:
            logger.error(f"Weather forecast error: {e}")
            return {'status': 'error', 'error': str(e)}

    async def get_recent_rain(self, hours: int) -> Dict:
        return await self.get_forecast(hours=-hours)

# --- IrrigationZone Class ---
class IrrigationZone:
    def __init__(self, zone_config: Dict):
        self.name, self.entity_id = zone_config['name'], zone_config['entity_id']
        self.duration, self.schedule, self.days = zone_config.get('duration', 10), zone_config.get('schedule', '05:00'), zone_config.get('days', ['mon', 'wed', 'fri'])
        self.enabled = zone_config.get('enabled', True)
        self.last_run, self.status, self.total_water_used = None, "idle", 0.0

    def should_run_today(self) -> bool:
        return self.enabled and datetime.now().strftime('%a').lower() in [d.lower()[:3] for d in self.days]
    
    def get_schedule_time(self) -> datetime:
        h, m = map(int, self.schedule.split(':'))
        return datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)

# --- SmartIrrigationController Class ---
class SmartIrrigationController:
    def __init__(self, config_path: str = "/data/options.json"):
        self.config = self._load_config(config_path)
        self.zones = [IrrigationZone(zc) for zc in self.config.get('zones', [])]
        self.weather = WeatherProvider(self.config['weather_provider'], self.config['weather_api_key'], self.config['latitude'], self.config['longitude'], self.config.get('units', 'metric'))
        self.history = HistoryManager()
        self.ha_token = os.environ.get('SUPERVISOR_TOKEN')
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.stats = {'total_runs': 0, 'water_saved': 0, 'last_weather_check': None}

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Config file not found or invalid. Using defaults.")
            return {'weather_provider': 'openweathermap', 'weather_api_key': 'YOUR_API_KEY', 'latitude': 36.8529, 'longitude': -75.9780, 'units': 'metric', 'zones': [{'name': 'Default', 'entity_id': 'switch.test'}], 'rain_forecast': {'enabled': True, 'threshold_mm': 5.0, 'hours_ahead': 24}, 'recent_rain': {'enabled': True, 'threshold_mm': 10.0, 'hours_back': 48}}

    async def check_weather_conditions(self) -> Dict:
        logger.info("Performing weather check...")
        conditions = {'skip_irrigation': False, 'details': {}}
        forecast = await self.weather.get_forecast(self.config['rain_forecast']['hours_ahead'])
        if forecast.get('status') == 'success' and forecast.get('rain_mm', 0) >= self.config['rain_forecast']['threshold_mm']:
            conditions['skip_irrigation'] = True; conditions['reason'] = "Forecast rain"
        
        recent = await self.weather.get_recent_rain(self.config['recent_rain']['hours_back'])
        if recent.get('status') == 'success':
            rain_mm = recent.get('rain_mm', 0)
            conditions['details']['recent_rain'] = rain_mm
            self.history.set_daily_rainfall(rain_mm) # Save to history
            if rain_mm >= self.config['recent_rain']['threshold_mm']:
                conditions['skip_irrigation'] = True; conditions['reason'] = "Recent rain"

        conditions['details']['forecast_rain'] = forecast.get('rain_mm', 0)
        conditions['details']['rain_chance'] = forecast.get('rain_chance', 0)
        self.stats['last_weather_check'] = datetime.now().isoformat()
        logger.info(f"Weather check complete. Skip: {conditions['skip_irrigation']}. Details: {conditions['details']}")
        return conditions

    async def control_valve(self, entity_id: str, state: str) -> bool: return True

    async def _run_zone_cancellable(self, zone: IrrigationZone, duration: int):
        zone.status, zone.last_run = "running", datetime.now()
        if not await self.control_valve(zone.entity_id, "on"):
            zone.status = "failed"; del self.running_tasks[zone.name]; return
        try:
            await asyncio.sleep(duration * 60)
            water_used = 15 * duration
            zone.total_water_used += water_used; self.history.log_data("water_used", water_used)
            zone.status = "completed"
        except asyncio.CancelledError:
            zone.status = "stopped"
            raise
        finally:
            await self.control_valve(zone.entity_id, "off")
            if zone.name in self.running_tasks: del self.running_tasks[zone.name]

    async def start_zone_task(self, zone, duration_override=None, test_mode=False):
        if zone.name in self.running_tasks: return
        duration = 1 if test_mode else duration_override or zone.duration
        self.running_tasks[zone.name] = asyncio.create_task(self._run_zone_cancellable(zone, duration))

    async def stop_zone_task(self, zone_name: str):
        if zone_name in self.running_tasks:
            self.running_tasks[zone_name].cancel()
            try: await self.running_tasks[zone_name]
            except asyncio.CancelledError: pass

    def get_status(self) -> Dict:
        serializable_zones = []
        for z in self.zones:
            zone_dict = z.__dict__.copy()
            if isinstance(zone_dict.get('last_run'), datetime):
                zone_dict['last_run'] = zone_dict['last_run'].isoformat()
            serializable_zones.append(zone_dict)
        return {'zones': serializable_zones, 'stats': self.stats, 'units': self.config.get('units', 'metric')}


# --- Flask Web Interface and Main Loop ---
template_dir = '/app/templates'
app = Flask(__name__, template_folder=template_dir)
irrigation_controller: Optional[SmartIrrigationController] = None
main_loop: Optional[asyncio.AbstractEventLoop] = None

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/status')
def api_status(): return jsonify(irrigation_controller.get_status()) if irrigation_controller else ({'error': 'Not ready'}, 503)

@app.route('/api/history')
def api_history(): return jsonify(irrigation_controller.history.get_last_7_days()) if irrigation_controller else ({'error': 'Not ready'}, 503)

@app.route('/api/weather_check')
def api_weather_check():
    future = asyncio.run_coroutine_threadsafe(irrigation_controller.check_weather_conditions(), main_loop)
    return jsonify(future.result(timeout=30))

def schedule_task(coro):
    if main_loop: asyncio.run_coroutine_threadsafe(coro, main_loop)

@app.route('/api/run_zone', methods=['POST'])
def api_run_zone():
    zone = next((z for z in irrigation_controller.zones if z.name == request.json.get('zone_name')), None)
    if zone:
        schedule_task(irrigation_controller.start_zone_task(zone, request.json.get('duration'), request.json.get('test_mode', False)))
        return jsonify({'success': True})
    return jsonify({'error': 'Zone not found'}), 404

@app.route('/api/stop_zone', methods=['POST'])
def api_stop_zone():
    schedule_task(irrigation_controller.stop_zone_task(request.json.get('zone_name')))
    return jsonify({'success': True})

def run_flask(): app.run(host='0.0.0.0', port=8080, debug=False)

async def background_weather_updater():
    """Periodically fetches weather and updates history."""
    while True:
        if irrigation_controller:
            logger.info("Running background weather update...")
            try:
                await irrigation_controller.check_weather_conditions()
            except Exception as e:
                logger.error(f"Error in background weather updater: {e}")
        # Wait for 1 hour before the next check
        await asyncio.sleep(3600)

async def main():
    global irrigation_controller, main_loop
    main_loop = asyncio.get_running_loop()
    irrigation_controller = SmartIrrigationController()
    
    # Start the Flask server in a separate thread
    web_thread = threading.Thread(target=run_flask, daemon=True)
    web_thread.start()
    
    # Start the background weather updater task
    main_loop.create_task(background_weather_updater())
    
    logger.info("Smart Irrigation Controller Initialized.")
    
    # The main loop can now be used for other periodic checks if needed,
    # for now it just keeps the program alive.
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down controller.")
