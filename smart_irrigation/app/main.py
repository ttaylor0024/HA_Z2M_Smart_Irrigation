#!/usr/bin/env python3
"""
Smart Irrigation Controller Add-on
Manages automated irrigation with weather integration
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
from flask import Flask, render_template, request, jsonify
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages reading and writing historical data for charting."""
    def __init__(self, history_file: str = "/data/history.json"):
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load history from JSON file."""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_history(self):
        """Save history to JSON file."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=4)

    def log_data(self, key: str, value: float):
        """Log a data point for the current day."""
        today_str = date.today().isoformat()
        if today_str not in self.history:
            self.history[today_str] = {"water_used": 0, "rainfall": 0}
        
        # Only add to the value
        self.history[today_str][key] = self.history[today_str].get(key, 0) + value
        self._save_history()

    def set_daily_rainfall(self, rainfall: float):
        """Set the total rainfall for the current day."""
        today_str = date.today().isoformat()
        if today_str not in self.history:
            self.history[today_str] = {"water_used": 0, "rainfall": 0}
        self.history[today_str]['rainfall'] = rainfall
        self._save_history()

    def get_last_7_days(self) -> Dict:
        """Get data for the last 7 days for charting."""
        labels = []
        water_data = []
        rain_data = []
        
        for i in range(6, -1, -1):
            day = date.today() - timedelta(days=i)
            day_str = day.isoformat()
            labels.append(day.strftime('%a')) # e.g., 'Mon'
            
            if day_str in self.history:
                water_data.append(self.history[day_str].get('water_used', 0))
                rain_data.append(self.history[day_str].get('rainfall', 0))
            else:
                water_data.append(0)
                rain_data.append(0)
                
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Water Used",
                    "data": water_data,
                    "borderColor": "#00a8ff",
                    "backgroundColor": "rgba(0, 168, 255, 0.2)",
                    "fill": True,
                    "yAxisID": "y"
                },
                {
                    "label": "Rainfall",
                    "data": rain_data,
                    "borderColor": "#00c853",
                    "backgroundColor": "rgba(0, 200, 83, 0.2)",
                    "fill": True,
                    "yAxisID": "y1"
                }
            ]
        }

class WeatherProvider:
    """Weather API integration supporting multiple providers"""
    
    def __init__(self, provider: str, api_key: str, lat: float, lon: float, units: str = "metric"):
        self.provider = provider
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.units = units  # metric or imperial
        
    async def get_forecast(self, hours: int) -> Dict:
        """Get weather forecast for specified hours ahead"""
        try:
            if self.provider == "openweathermap":
                return await self._get_openweather_forecast(hours)
            elif self.provider == "weatherapi":
                return await self._get_weatherapi_forecast(hours)
            elif self.provider == "visualcrossing":
                return await self._get_visualcrossing_forecast(hours)
            else:
                raise ValueError(f"Unsupported weather provider: {self.provider}")
        except Exception as e:
            logger.error(f"Weather forecast error: {e}")
            return {'rain_mm': 0, 'rain_chance': 0, 'status': 'error', 'error': str(e)}
    
    async def get_recent_rain(self, hours: int) -> Dict:
        """Get rainfall amount for past hours"""
        try:
            if self.provider == "openweathermap":
                return await self._get_openweather_history(hours)
            elif self.provider == "weatherapi":
                return await self._get_weatherapi_history(hours)
            elif self.provider == "visualcrossing":
                return await self._get_visualcrossing_history(hours)
            else:
                raise ValueError(f"Unsupported weather provider: {self.provider}")
        except Exception as e:
            logger.error(f"Weather history error: {e}")
            return {'rain_mm': 0, 'status': 'error', 'error': str(e)}
    
    async def _get_openweather_forecast(self, hours: int) -> Dict:
        """OpenWeatherMap forecast implementation"""
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': self.lat,
            'lon': self.lon,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_rain = 0.0
                    rain_chance = 0.0
                    count = 0
                    end_time = datetime.now() + timedelta(hours=hours)
                    
                    for item in data['list']:
                        forecast_time = datetime.fromtimestamp(item['dt'])
                        if forecast_time <= end_time:
                            rain = item.get('rain', {}).get('3h', 0)
                            total_rain += rain
                            pop = item.get('pop', 0) * 100  # Probability of precipitation
                            rain_chance = max(rain_chance, pop)
                            count += 1
                    
                    # Convert to inches if needed
                    if self.units == "imperial":
                        total_rain = total_rain * 0.0393701
                    
                    return {
                        'rain_mm': total_rain,
                        'rain_chance': rain_chance,
                        'status': 'success'
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"OpenWeatherMap API error: {response.status} - {error_text}")
                    return {'rain_mm': 0, 'rain_chance': 0, 'status': 'error', 'error': error_text}
    
    async def _get_weatherapi_forecast(self, hours: int) -> Dict:
        """WeatherAPI forecast implementation"""
        days = min(3, (hours // 24) + 1)
        url = f"http://api.weatherapi.com/v1/forecast.json"
        params = {
            'key': self.api_key,
            'q': f"{self.lat},{self.lon}",
            'days': days
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_rain = 0.0
                    rain_chance = 0.0
                    end_time = datetime.now() + timedelta(hours=hours)
                    
                    for day in data['forecast']['forecastday']:
                        day_date = datetime.strptime(day['date'], '%Y-%m-%d')
                        if day_date.date() <= end_time.date():
                            # Add daily rain
                            if self.units == "metric":
                                total_rain += day['day']['totalprecip_mm']
                            else:
                                total_rain += day['day']['totalprecip_in']
                            
                            # Check hourly data for rain chance
                            for hour in day['hour']:
                                hour_time = datetime.strptime(hour['time'], '%Y-%m-%d %H:%M')
                                if hour_time <= end_time:
                                    rain_chance = max(rain_chance, hour['chance_of_rain'])
                    
                    return {
                        'rain_mm': total_rain,
                        'rain_chance': rain_chance,
                        'status': 'success'
                    }
                else:
                    error_text = await response.text()
                    return {'rain_mm': 0, 'rain_chance': 0, 'status': 'error', 'error': error_text}
    
    async def _get_visualcrossing_forecast(self, hours: int) -> Dict:
        """Visual Crossing Weather API forecast implementation"""
        end_date = (datetime.now() + timedelta(hours=hours)).strftime('%Y-%m-%d')
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{self.lat},{self.lon}/{datetime.now().strftime('%Y-%m-%d')}/{end_date}"
        params = {
            'key': self.api_key,
            'unitGroup': 'metric' if self.units == "metric" else 'us',
            'include': 'hours'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_rain = 0.0
                    rain_chance = 0.0
                    
                    for day in data['days']:
                        total_rain += day.get('precip', 0)
                        rain_chance = max(rain_chance, day.get('precipprob', 0))
                    
                    return {
                        'rain_mm': total_rain,
                        'rain_chance': rain_chance,
                        'status': 'success'
                    }
                else:
                    error_text = await response.text()
                    return {'rain_mm': 0, 'rain_chance': 0, 'status': 'error', 'error': error_text}
    
    async def _get_openweather_history(self, hours: int) -> Dict:
        """OpenWeatherMap One Call API for recent data"""
        # Note: This requires OpenWeatherMap One Call API 3.0
        url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine"
        timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        params = {
            'lat': self.lat,
            'lon': self.lon,
            'dt': timestamp,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_rain = data.get('data', [{}])[0].get('rain', {}).get('1h', 0)
                    
                    if self.units == "imperial":
                        total_rain = total_rain * 0.0393701
                    
                    return {'rain_mm': total_rain, 'status': 'success'}
                else:
                    # Fallback to current weather if history not available
                    return await self._get_current_weather_rain()
    
    async def _get_weatherapi_history(self, hours: int) -> Dict:
        """WeatherAPI history implementation"""
        date = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d')
        url = f"http://api.weatherapi.com/v1/history.json"
        params = {
            'key': self.api_key,
            'q': f"{self.lat},{self.lon}",
            'dt': date
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if self.units == "metric":
                        total_rain = data['forecast']['forecastday'][0]['day']['totalprecip_mm']
                    else:
                        total_rain = data['forecast']['forecastday'][0]['day']['totalprecip_in']
                    
                    return {'rain_mm': total_rain, 'status': 'success'}
                else:
                    return {'rain_mm': 0, 'status': 'error'}
    
    async def _get_visualcrossing_history(self, hours: int) -> Dict:
        """Visual Crossing history implementation"""
        date = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d')
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{self.lat},{self.lon}/{date}"
        params = {
            'key': self.api_key,
            'unitGroup': 'metric' if self.units == "metric" else 'us',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_rain = data['days'][0].get('precip', 0)
                    return {'rain_mm': total_rain, 'status': 'success'}
                else:
                    return {'rain_mm': 0, 'status': 'error'}
    
    async def _get_current_weather_rain(self) -> Dict:
        """Fallback to get current weather conditions"""
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': self.lat,
            'lon': self.lon,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Rain in last hour
                    rain = data.get('rain', {}).get('1h', 0)
                    if self.units == "imperial":
                        rain = rain * 0.0393701
                    return {'rain_mm': rain, 'status': 'success'}
                else:
                    return {'rain_mm': 0, 'status': 'error'}

class IrrigationZone:
    """Represents an irrigation zone with its configuration"""
    
    def __init__(self, zone_config: Dict):
        self.name = zone_config['name']
        self.entity_id = zone_config['entity_id']
        self.duration = zone_config['duration']  # minutes
        self.schedule = zone_config['schedule']  # HH:MM format
        self.days = zone_config['days']
        self.enabled = zone_config.get('enabled', True)
        self.flow_sensor = zone_config.get('flow_sensor', '')
        self.moisture_sensor = zone_config.get('moisture_sensor', '')
        self.moisture_threshold = zone_config.get('moisture_threshold', 30)
        self.zone_type = zone_config.get('zone_type', 'lawn')  # lawn, garden, drip
        self.last_run = None
        self.status = "idle"
        self.current_flow = 0.0
        self.total_water_used = 0.0
    
    def should_run_today(self) -> bool:
        """Check if zone should run today based on schedule"""
        if not self.enabled:
            return False
        today = datetime.now().strftime('%a').lower()
        return today in [day.lower()[:3] for day in self.days]
    
    def get_schedule_time(self) -> datetime:
        """Get today's scheduled run time"""
        time_parts = self.schedule.split(':')
        today = datetime.now().replace(
            hour=int(time_parts[0]), 
            minute=int(time_parts[1]), 
            second=0, 
            microsecond=0
        )
        return today

class SmartIrrigationController:
    """Main irrigation controller"""
    
    def __init__(self, config_path: str = "/data/options.json"):
        self.config = self._load_config(config_path)
        self.zones = self._create_zones()
        self.weather = WeatherProvider(
            self.config['weather_provider'],
            self.config['weather_api_key'],
            self.config['latitude'],
            self.config['longitude'],
            self.config.get('units', 'metric')
        )
        self.history = HistoryManager()
        self.ha_token = os.environ.get('SUPERVISOR_TOKEN')
        self.ha_url = "http://supervisor/core"
        self.running_tasks: Dict[str, asyncio.Task] = {} # For cancellable tasks
        self.stats = {
            'total_runs': 0,
            'water_saved': 0,
            'last_weather_check': None,
            'weather_skip_count': 0
        }
        
    def _load_config(self, config_path: str = "/data/options.json") -> Dict:
        """Load add-on configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}, using defaults.")
            return {
                'weather_provider': 'openweathermap', 'weather_api_key': 'YOUR_API_KEY',
                'latitude': 36.8529, 'longitude': -75.9780, 'units': 'imperial',
                'zones': [{'name': 'Default Zone', 'entity_id': 'switch.test', 'enabled': True, 'zone_type': 'lawn', 'duration': 10, 'schedule': '05:00', 'days': ['mon', 'wed', 'fri']}],
                'rain_forecast': {'enabled': True, 'threshold_mm': 5.0, 'hours_ahead': 24, 'skip_percentage': 70},
                'recent_rain': {'enabled': True, 'threshold_mm': 10.0, 'hours_back': 48} # Increased to 48h
            }
    
    def _create_zones(self) -> List[IrrigationZone]:
        return [IrrigationZone(zc) for zc in self.config.get('zones', [])]
    
    async def get_sensor_value(self, entity_id: str) -> Optional[float]:
        # ... (no changes) ...
        return None # Placeholder
    
    async def check_weather_conditions(self) -> Dict:
        """Check weather conditions for irrigation decision"""
        conditions = {'skip_irrigation': False, 'reduce_duration': False, 'reduction_factor': 1.0, 'reason': '', 'details': {}}
        self.stats['last_weather_check'] = datetime.now()
        
        # Check forecast rain
        if self.config['rain_forecast']['enabled']:
            forecast = await self.weather.get_forecast(self.config['rain_forecast']['hours_ahead'])
            if forecast['status'] == 'success':
                conditions['details']['forecast_rain'] = forecast['rain_mm']
                if forecast['rain_mm'] >= self.config['rain_forecast']['threshold_mm']:
                    conditions['skip_irrigation'] = True; conditions['reason'] = "Forecast rain exceeds threshold"

        # Check recent rain (fixed logic)
        if self.config['recent_rain']['enabled'] and not conditions['skip_irrigation']:
            recent = await self.weather.get_recent_rain(self.config['recent_rain']['hours_back'])
            if recent['status'] == 'success':
                conditions['details']['recent_rain'] = recent['rain_mm']
                self.history.set_daily_rainfall(recent['rain_mm']) # Log to history
                if recent['rain_mm'] >= self.config['recent_rain']['threshold_mm']:
                    conditions['skip_irrigation'] = True; conditions['reason'] = "Recent rain exceeds threshold"

        return conditions
    
    async def control_valve(self, entity_id: str, state: str) -> bool:
        # ... (no changes) ...
        logger.info(f"Simulating valve control: {entity_id} -> {state}")
        return True # Placeholder for actual control

    async def _run_zone_cancellable(self, zone: IrrigationZone, duration: int):
        """Internal cancellable method for running a zone."""
        logger.info(f"Starting irrigation for {zone.name} ({duration} minutes)")
        zone.status = "running"
        zone.last_run = datetime.now()

        if await self.control_valve(zone.entity_id, "on"):
            try:
                start_time = time.time()
                water_this_run = 0
                flow_lpm = 15 # Assume 15 L/min if no sensor
                
                # Sleep for the duration, allowing for cancellation
                await asyncio.sleep(duration * 60)
                
                # This part is reached if sleep completes without cancellation
                water_this_run = flow_lpm * duration
                zone.total_water_used += water_this_run
                self.history.log_data("water_used", water_this_run) # Log to history
                self.stats['total_runs'] += 1
                zone.status = "completed"
                logger.info(f"Completed irrigation for {zone.name}. Water used: {water_this_run:.1f}L")

            except asyncio.CancelledError:
                zone.status = "stopped"
                logger.info(f"Stopped irrigation for {zone.name}")
                raise
            finally:
                await self.control_valve(zone.entity_id, "off")
                zone.current_flow = 0.0
                if zone.name in self.running_tasks:
                    del self.running_tasks[zone.name]
        else:
            zone.status = "failed"
            if zone.name in self.running_tasks: del self.running_tasks[zone.name]

    async def start_zone_task(self, zone: IrrigationZone, duration_override: Optional[int] = None, test_mode: bool = False):
        """Creates and starts a cancellable task for a zone."""
        if zone.name in self.running_tasks:
            logger.warning(f"Zone {zone.name} is already running.")
            return

        duration = 1 if test_mode else duration_override or zone.duration
        task = asyncio.create_task(self._run_zone_cancellable(zone, duration))
        self.running_tasks[zone.name] = task

    async def stop_zone_task(self, zone_name: str):
        """Stops a running irrigation task."""
        if zone_name in self.running_tasks:
            task = self.running_tasks[zone_name]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass # Expected
            logger.info(f"Successfully sent stop command to {zone_name}")
            return True
        return False
    
    # ... (get_status and other methods) ...
    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            'zones': [
                {'name': z.name, 'entity_id': z.entity_id, 'status': z.status, 'enabled': z.enabled, 'zone_type': z.zone_type, 'duration': z.duration, 'schedule': z.schedule, 'days': z.days, 'last_run': z.last_run.isoformat() if z.last_run else None, 'next_scheduled': z.get_schedule_time().isoformat() if z.should_run_today() else None, 'current_flow': z.current_flow, 'total_water_used': z.total_water_used, 'moisture_sensor': z.moisture_sensor, 'moisture_threshold': z.moisture_threshold, 'flow_sensor': z.flow_sensor} for z in self.zones
            ],
            'weather_provider': self.config['weather_provider'], 'units': self.config.get('units', 'metric'), 'stats': self.stats
        }

# Flask web interface
template_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=template_dir)
irrigation_controller: Optional[SmartIrrigationController] = None
main_loop: Optional[asyncio.AbstractEventLoop] = None

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/status')
def api_status(): return jsonify(irrigation_controller.get_status()) if irrigation_controller else ({}, 503)

@app.route('/api/history')
def api_history(): return jsonify(irrigation_controller.history.get_last_7_days()) if irrigation_controller else ({}, 503)

@app.route('/api/weather_check')
def api_weather_check():
    if irrigation_controller and main_loop:
        future = asyncio.run_coroutine_threadsafe(irrigation_controller.check_weather_conditions(), main_loop)
        return jsonify(future.result(timeout=30))
    return jsonify({'error': 'Controller not ready'}), 503

def schedule_task(coro):
    """Helper to schedule a fire-and-forget task from a Flask route."""
    if main_loop: asyncio.run_coroutine_threadsafe(coro, main_loop)

@app.route('/api/run_zone', methods=['POST'])
def api_run_zone():
    data = request.json
    zone = next((z for z in irrigation_controller.zones if z.name == data.get('zone_name')), None)
    if zone:
        schedule_task(irrigation_controller.start_zone_task(zone, data.get('duration'), data.get('test_mode', False)))
        return jsonify({'success': True})
    return jsonify({'error': 'Zone not found'}), 404

@app.route('/api/stop_zone', methods=['POST'])
def api_stop_zone():
    zone_name = request.json.get('zone_name')
    if zone_name:
        schedule_task(irrigation_controller.stop_zone_task(zone_name))
        return jsonify({'success': True})
    return jsonify({'error': 'Zone name not provided'}), 400

# ... (other api routes can be simplified with schedule_task) ...

def run_flask():
    app.run(host='0.0.0.0', port=8099, debug=False) # Changed port to avoid conflicts

async def main_loop_logic():
    global irrigation_controller, main_loop
    main_loop = asyncio.get_running_loop()
    irrigation_controller = SmartIrrigationController()
    
    web_thread = threading.Thread(target=run_flask); web_thread.daemon = True; web_thread.start()
    logger.info("Smart Irrigation Controller Initialized")
    
    while True:
        # Scheduled run logic would go here
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main_loop_logic())
