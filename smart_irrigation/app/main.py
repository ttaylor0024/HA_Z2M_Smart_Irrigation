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
        self.ha_token = os.environ.get('SUPERVISOR_TOKEN')
        self.ha_url = "http://supervisor/core"
        self.stats = {
            'total_runs': 0,
            'water_saved': 0,
            'last_weather_check': None,
            'weather_skip_count': 0
        }
        
    def _load_config(self, config_path: str) -> Dict:
        """Load add-on configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            # Return default config
            return {
                'weather_provider': 'openweathermap',
                'weather_api_key': '',
                'latitude': 0.0,
                'longitude': 0.0,
                'units': 'metric',
                'zones': []
            }
    
    def _create_zones(self) -> List[IrrigationZone]:
        """Create zone objects from configuration"""
        zones = []
        for zone_config in self.config.get('zones', []):
            zone = IrrigationZone(zone_config)
            zones.append(zone)
        return zones
    
    async def get_sensor_value(self, entity_id: str) -> Optional[float]:
        """Get sensor value from Home Assistant"""
        if not entity_id:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.ha_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.ha_url}/api/states/{entity_id}"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    try:
                        return float(data['state'])
                    except (ValueError, KeyError):
                        return None
                else:
                    return None
    
    async def check_weather_conditions(self) -> Dict:
        """Check weather conditions for irrigation decision"""
        conditions = {
            'skip_irrigation': False,
            'reduce_duration': False,
            'reduction_factor': 1.0,
            'reason': '',
            'details': {}
        }
        
        self.stats['last_weather_check'] = datetime.now()
        
        # Check forecast rain
        if self.config['rain_forecast']['enabled']:
            forecast = await self.weather.get_forecast(
                self.config['rain_forecast']['hours_ahead']
            )
            
            if forecast['status'] == 'success':
                forecast_rain = forecast['rain_mm']
                rain_chance = forecast.get('rain_chance', 0)
                threshold = self.config['rain_forecast']['threshold_mm']
                skip_percentage = self.config['rain_forecast']['skip_percentage']
                
                conditions['details']['forecast_rain'] = forecast_rain
                conditions['details']['rain_chance'] = rain_chance
                
                # Check rain chance threshold
                if rain_chance >= skip_percentage:
                    conditions['skip_irrigation'] = True
                    conditions['reason'] = f"Rain chance {rain_chance:.0f}% exceeds threshold"
                    self.stats['weather_skip_count'] += 1
                elif forecast_rain >= threshold:
                    conditions['skip_irrigation'] = True
                    conditions['reason'] = f"Forecast rain: {forecast_rain:.1f}mm exceeds threshold"
                    self.stats['weather_skip_count'] += 1
        
        # Check recent rain
        if self.config['recent_rain']['enabled'] and not conditions['skip_irrigation']:
            recent = await self.weather.get_recent_rain(
                self.config['recent_rain']['hours_back']
            )
            
            if recent['status'] == 'success':
                recent_rain = recent['rain_mm']
                threshold = self.config['recent_rain']['threshold_mm']
                
                conditions['details']['recent_rain'] = recent_rain
                
                if recent_rain >= threshold:
                    if self.config['recent_rain']['compensation_enabled']:
                        # Calculate reduction based on recent rain
                        ratio = self.config['recent_rain']['compensation_ratio']
                        reduction = min(ratio, recent_rain / (threshold * 2))
                        conditions['reduce_duration'] = True
                        conditions['reduction_factor'] = 1.0 - reduction
                        conditions['reason'] = f"Recent rain: {recent_rain:.1f}mm, reducing duration by {reduction*100:.0f}%"
                    else:
                        conditions['skip_irrigation'] = True
                        conditions['reason'] = f"Recent rain: {recent_rain:.1f}mm exceeds threshold"
                        self.stats['weather_skip_count'] += 1
        
        return conditions
    
    async def check_zone_sensors(self, zone: IrrigationZone) -> Dict:
        """Check zone-specific sensors"""
        sensor_conditions = {
            'skip': False,
            'reason': '',
            'moisture': None,
            'flow': None
        }
        
        # Check moisture sensor
        if zone.moisture_sensor:
            moisture = await self.get_sensor_value(zone.moisture_sensor)
            if moisture is not None:
                sensor_conditions['moisture'] = moisture
                if moisture >= zone.moisture_threshold:
                    sensor_conditions['skip'] = True
                    sensor_conditions['reason'] = f"Soil moisture {moisture}% above threshold"
        
        # Check flow sensor
        if zone.flow_sensor:
            flow = await self.get_sensor_value(zone.flow_sensor)
            if flow is not None:
                sensor_conditions['flow'] = flow
                zone.current_flow = flow
        
        return sensor_conditions
    
    async def control_valve(self, entity_id: str, state: str) -> bool:
        """Control Home Assistant entity (valve)"""
        headers = {
            'Authorization': f'Bearer {self.ha_token}',
            'Content-Type': 'application/json'
        }
        
        # Determine the domain from entity_id
        domain = entity_id.split('.')[0]
        service = f"{domain}.turn_{state}"
        
        data = {
            'entity_id': entity_id
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.ha_url}/api/services/{service.replace('.', '/')}"
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    logger.info(f"Successfully turned {state} {entity_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to control {entity_id}: {response.status} - {error_text}")
                    return False
    
    async def run_zone(self, zone: IrrigationZone, duration_override: Optional[int] = None, test_mode: bool = False):
        """Run irrigation for a specific zone"""
        duration = duration_override or zone.duration
        
        if test_mode:
            duration = min(duration, 1)  # Max 1 minute for test mode
        
        logger.info(f"Starting irrigation for {zone.name} ({duration} minutes) - Test mode: {test_mode}")
        zone.status = "running"
        zone.last_run = datetime.now()
        
        # Turn on valve
        if await self.control_valve(zone.entity_id, "on"):
            start_time = time.time()
            water_used = 0.0
            
            # Monitor water flow during irrigation
            while time.time() - start_time < duration * 60:
                if zone.flow_sensor:
                    flow = await self.get_sensor_value(zone.flow_sensor)
                    if flow:
                        zone.current_flow = flow
                        water_used += flow * 0.1  # Assuming flow in L/min, update every 6 seconds
                
                await asyncio.sleep(6)  # Check every 6 seconds
            
            # Turn off valve
            await self.control_valve(zone.entity_id, "off")
            zone.status = "completed"
            zone.current_flow = 0.0
            zone.total_water_used += water_used
            self.stats['total_runs'] += 1
            
            logger.info(f"Completed irrigation for {zone.name} - Water used: {water_used:.1f}L")
        else:
            zone.status = "failed"
            logger.error(f"Failed to start irrigation for {zone.name}")
    
    async def run_all_zones(self, test_mode: bool = False):
        """Run all enabled zones"""
        for zone in self.zones:
            if zone.enabled:
                await self.run_zone(zone, test_mode=test_mode)
                # Wait between zones
                await asyncio.sleep(30)
    
    async def process_scheduled_irrigation(self):
        """Process all scheduled irrigation zones"""
        logger.info("Processing scheduled irrigation")
        
        # Check weather conditions once for all zones
        weather_conditions = await self.check_weather_conditions()
        
        if weather_conditions['skip_irrigation']:
            logger.info(f"Skipping all irrigation: {weather_conditions['reason']}")
            # Record water saved
            total_duration = sum(z.duration for z in self.zones if z.enabled and z.should_run_today())
            self.stats['water_saved'] += total_duration * 10  # Assuming 10L/min average
            return
        
        for zone in self.zones:
            if zone.should_run_today():
                schedule_time = zone.get_schedule_time()
                current_time = datetime.now()
                
                # Check if it's time to run (within 1 minute window)
                if abs((current_time - schedule_time).total_seconds()) <= 60:
                    # Check zone-specific sensors
                    sensor_conditions = await self.check_zone_sensors(zone)
                    
                    if sensor_conditions['skip']:
                        logger.info(f"Skipping {zone.name}: {sensor_conditions['reason']}")
                        self.stats['water_saved'] += zone.duration * 10
                        continue
                    
                    duration = zone.duration
                    
                    # Apply weather-based duration reduction
                    if weather_conditions['reduce_duration']:
                        duration = int(duration * weather_conditions['reduction_factor'])
                        saved = zone.duration - duration
                        self.stats['water_saved'] += saved * 10
                        logger.info(f"Reducing {zone.name} duration to {duration} minutes: {weather_conditions['reason']}")
                    
                    await self.run_zone(zone, duration)
    
    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            'zones': [
                {
                    'name': zone.name,
                    'entity_id': zone.entity_id,
                    'status': zone.status,
                    'enabled': zone.enabled,
                    'zone_type': zone.zone_type,
                    'duration': zone.duration,
                    'schedule': zone.schedule,
                    'days': zone.days,
                    'last_run': zone.last_run.isoformat() if zone.last_run else None,
                    'next_scheduled': zone.get_schedule_time().isoformat() if zone.should_run_today() else None,
                    'current_flow': zone.current_flow,
                    'total_water_used': zone.total_water_used,
                    'moisture_sensor': zone.moisture_sensor,
                    'moisture_threshold': zone.moisture_threshold,
                    'flow_sensor': zone.flow_sensor
                }
                for zone in self.zones
            ],
            'weather_provider': self.config['weather_provider'],
            'units': self.config.get('units', 'metric'),
            'stats': self.stats,
            'config': self.config
        }

# Flask web interface
app = Flask(__name__)
irrigation_controller = None

@app.route('/')
def index():
    """Main dashboard"""
    if irrigation_controller:
        status = irrigation_controller.get_status()
        return render_template('index.html', status=status)
    return "Irrigation controller not initialized"

@app.route('/api/status')
def api_status():
    """API endpoint for status"""
    if irrigation_controller:
        return jsonify(irrigation_controller.get_status())
    return jsonify({'error': 'Controller not initialized'})

@app.route('/api/run_zone', methods=['POST'])
def api_run_zone():
    """API endpoint to manually run a zone"""
    data = request.json
    zone_name = data.get('zone_name')
    duration = data.get('duration')
    test_mode = data.get('test_mode', False)
    
    if irrigation_controller:
        zone = next((z for z in irrigation_controller.zones if z.name == zone_name), None)
        if zone:
            asyncio.create_task(irrigation_controller.run_zone(zone, duration, test_mode))
            return jsonify({'success': True, 'message': f'Started {zone_name}'})
    
    return jsonify({'error': 'Zone not found'})

@app.route('/api/run_all', methods=['POST'])
def api_run_all():
    """API endpoint to run all zones"""
    data = request.json
    test_mode = data.get('test_mode', False)
    
    if irrigation_controller:
        asyncio.create_task(irrigation_controller.run_all_zones(test_mode))
        return jsonify({'success': True, 'message': 'Started all zones'})
    
    return jsonify({'error': 'Controller not initialized'})

@app.route('/api/weather_check', methods=['GET'])
async def api_weather_check():
    """API endpoint to check current weather conditions"""
    if irrigation_controller:
        conditions = await irrigation_controller.check_weather_conditions()
        return jsonify(conditions)
    return jsonify({'error': 'Controller not initialized'})

@app.route('/api/toggle_zone', methods=['POST'])
def api_toggle_zone():
    """API endpoint to enable/disable a zone"""
    data = request.json
    zone_name = data.get('zone_name')
    enabled = data.get('enabled')
    
    if irrigation_controller:
        zone = next((z for z in irrigation_controller.zones if z.name == zone_name), None)
        if zone:
            zone.enabled = enabled
            return jsonify({'success': True})
    
    return jsonify({'error': 'Zone not found'})

@app.route('/api/update_zone', methods=['POST'])
def api_update_zone():
    """API endpoint to update zone settings"""
    data = request.json
    zone_name = data.get('zone_name')
    
    if irrigation_controller:
        zone = next((z for z in irrigation_controller.zones if z.name == zone_name), None)
        if zone:
            # Update zone settings
            if 'duration' in data:
                zone.duration = data['duration']
            if 'schedule' in data:
                zone.schedule = data['schedule']
            if 'days' in data:
                zone.days = data['days']
            if 'moisture_threshold' in data:
                zone.moisture_threshold = data['moisture_threshold']
            
            return jsonify({'success': True})
    
    return jsonify({'error': 'Zone not found'})

async def main():
    """Main application entry point"""
    global irrigation_controller
    
    logger.info("Starting Smart Irrigation Controller")
    
    # Initialize controller
    irrigation_controller = SmartIrrigationController()
    
    # Main loop - check every minute without schedule library
    while True:
        # Run irrigation check every minute
        await irrigation_controller.process_scheduled_irrigation()
        await asyncio.sleep(60)  # Wait 60 seconds
    
    # Start web server in separate thread
    def run_web_server():
        app.run(host='0.0.0.0', port=8080, debug=False)
    
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

if __name__ == "__main__":
    asyncio.run(main())
