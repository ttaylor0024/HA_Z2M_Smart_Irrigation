#!/usr/bin/env python3
"""
Smart Irrigation Controller Add-on
Manages automated irrigation with weather integration
"""

import asyncio
import logging
import json
import yaml
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import schedule
from flask import Flask, render_template, request, jsonify
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherProvider:
    """Weather API integration"""
    
    def __init__(self, provider: str, api_key: str, lat: float, lon: float):
        self.provider = provider
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        
    async def get_forecast(self, hours: int) -> Dict:
        """Get weather forecast for specified hours ahead"""
        if self.provider == "openweathermap":
            return await self._get_openweather_forecast(hours)
        elif self.provider == "weatherapi":
            return await self._get_weatherapi_forecast(hours)
        else:
            raise ValueError(f"Unsupported weather provider: {self.provider}")
    
    async def get_recent_rain(self, hours: int) -> float:
        """Get rainfall amount for past hours"""
        if self.provider == "openweathermap":
            return await self._get_openweather_history(hours)
        elif self.provider == "weatherapi":
            return await self._get_weatherapi_history(hours)
        else:
            raise ValueError(f"Unsupported weather provider: {self.provider}")
    
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
                    end_time = datetime.now() + timedelta(hours=hours)
                    
                    for item in data['list']:
                        forecast_time = datetime.fromtimestamp(item['dt'])
                        if forecast_time <= end_time:
                            rain = item.get('rain', {}).get('3h', 0)
                            total_rain += rain
                    
                    return {'rain_mm': total_rain, 'status': 'success'}
                else:
                    logger.error(f"Weather API error: {response.status}")
                    return {'rain_mm': 0, 'status': 'error'}
    
    async def _get_openweather_history(self, hours: int) -> float:
        """OpenWeatherMap historical data implementation"""
        # Note: This requires OpenWeatherMap's historical API
        start_time = int((datetime.now() - timedelta(hours=hours)).timestamp())
        end_time = int(datetime.now().timestamp())
        
        url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine"
        params = {
            'lat': self.lat,
            'lon': self.lon,
            'dt': start_time,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        # Simplified implementation - would need multiple calls for full history
        return 0.0

class IrrigationZone:
    """Represents an irrigation zone with its configuration"""
    
    def __init__(self, name: str, entity_id: str, duration: int, 
                 schedule: str, days: List[str]):
        self.name = name
        self.entity_id = entity_id
        self.duration = duration  # minutes
        self.schedule = schedule  # HH:MM format
        self.days = days
        self.last_run = None
        self.status = "idle"
    
    def should_run_today(self) -> bool:
        """Check if zone should run today based on schedule"""
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
            self.config['longitude']
        )
        self.ha_token = os.environ.get('SUPERVISOR_TOKEN')
        self.ha_url = "http://supervisor/core"
        
    def _load_config(self, config_path: str) -> Dict:
        """Load add-on configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            return {}
    
    def _create_zones(self) -> List[IrrigationZone]:
        """Create zone objects from configuration"""
        zones = []
        for zone_config in self.config.get('zones', []):
            zone = IrrigationZone(
                zone_config['name'],
                zone_config['entity_id'],
                zone_config['duration'],
                zone_config['schedule'],
                zone_config['days']
            )
            zones.append(zone)
        return zones
    
    async def check_weather_conditions(self) -> Dict:
        """Check weather conditions for irrigation decision"""
        conditions = {
            'skip_irrigation': False,
            'reduce_duration': False,
            'reduction_factor': 1.0,
            'reason': ''
        }
        
        # Check forecast rain
        if self.config['rain_forecast']['enabled']:
            forecast = await self.weather.get_forecast(
                self.config['rain_forecast']['hours_ahead']
            )
            
            if forecast['status'] == 'success':
                forecast_rain = forecast['rain_mm']
                threshold = self.config['rain_forecast']['threshold_mm']
                skip_percentage = self.config['rain_forecast']['skip_percentage']
                
                if forecast_rain >= threshold:
                    skip_chance = min(100, (forecast_rain / threshold) * skip_percentage)
                    if skip_chance >= 80:  # High confidence skip
                        conditions['skip_irrigation'] = True
                        conditions['reason'] = f"Heavy rain forecast: {forecast_rain:.1f}mm"
        
        # Check recent rain
        if self.config['recent_rain']['enabled']:
            recent_rain = await self.weather.get_recent_rain(
                self.config['recent_rain']['hours_back']
            )
            
            threshold = self.config['recent_rain']['threshold_mm']
            if recent_rain >= threshold:
                if self.config['recent_rain']['compensation_enabled']:
                    # Reduce irrigation duration based on recent rain
                    reduction = min(0.8, recent_rain / (threshold * 2))
                    conditions['reduce_duration'] = True
                    conditions['reduction_factor'] = 1.0 - reduction
                    conditions['reason'] = f"Recent rain: {recent_rain:.1f}mm, reduced duration"
                else:
                    conditions['skip_irrigation'] = True
                    conditions['reason'] = f"Recent rain: {recent_rain:.1f}mm"
        
        return conditions
    
    async def control_valve(self, entity_id: str, state: str) -> bool:
        """Control Home Assistant entity (valve)"""
        headers = {
            'Authorization': f'Bearer {self.ha_token}',
            'Content-Type': 'application/json'
        }
        
        service = "switch.turn_on" if state == "on" else "switch.turn_off"
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
                    logger.error(f"Failed to control {entity_id}: {response.status}")
                    return False
    
    async def run_zone(self, zone: IrrigationZone, duration_override: Optional[int] = None):
        """Run irrigation for a specific zone"""
        duration = duration_override or zone.duration
        
        logger.info(f"Starting irrigation for {zone.name} ({duration} minutes)")
        zone.status = "running"
        zone.last_run = datetime.now()
        
        # Turn on valve
        if await self.control_valve(zone.entity_id, "on"):
            # Wait for duration
            await asyncio.sleep(duration * 60)
            # Turn off valve
            await self.control_valve(zone.entity_id, "off")
            zone.status = "completed"
            logger.info(f"Completed irrigation for {zone.name}")
        else:
            zone.status = "failed"
            logger.error(f"Failed to start irrigation for {zone.name}")
    
    async def process_scheduled_irrigation(self):
        """Process all scheduled irrigation zones"""
        logger.info("Processing scheduled irrigation")
        
        # Check weather conditions
        weather_conditions = await self.check_weather_conditions()
        
        if weather_conditions['skip_irrigation']:
            logger.info(f"Skipping irrigation: {weather_conditions['reason']}")
            return
        
        for zone in self.zones:
            if zone.should_run_today():
                schedule_time = zone.get_schedule_time()
                current_time = datetime.now()
                
                # Check if it's time to run (within 5 minute window)
                if abs((current_time - schedule_time).total_seconds()) <= 300:
                    duration = zone.duration
                    
                    # Apply weather-based duration reduction
                    if weather_conditions['reduce_duration']:
                        duration = int(duration * weather_conditions['reduction_factor'])
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
                    'last_run': zone.last_run.isoformat() if zone.last_run else None,
                    'next_scheduled': zone.get_schedule_time().isoformat() if zone.should_run_today() else None
                }
                for zone in self.zones
            ],
            'weather_provider': self.config['weather_provider'],
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
    
    if irrigation_controller:
        zone = next((z for z in irrigation_controller.zones if z.name == zone_name), None)
        if zone:
            asyncio.create_task(irrigation_controller.run_zone(zone, duration))
            return jsonify({'success': True})
    
    return jsonify({'error': 'Zone not found'})

async def main():
    """Main application entry point"""
    global irrigation_controller
    
    logger.info("Starting Smart Irrigation Controller")
    
    # Initialize controller
    irrigation_controller = SmartIrrigationController()
    
    # Schedule regular checks
    schedule.every(1).minutes.do(lambda: asyncio.create_task(irrigation_controller.process_scheduled_irrigation()))
    
    # Start web server in separate thread
    def run_web_server():
        app.run(host='0.0.0.0', port=8080, debug=False)
    
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # Main loop
    while True:
        schedule.run_pending()
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
