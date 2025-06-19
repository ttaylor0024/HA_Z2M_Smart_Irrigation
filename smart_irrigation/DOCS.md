# Home Assistant Add-on: Smart Irrigation Controller

Automated irrigation system with weather intelligence and Z2M valve control - designed for ease of use with minimal configuration required.

## 🌟 Features

- **Weather-Smart Irrigation**: Automatically adjusts or skips watering based on weather conditions
- **Multi-Zone Support**: Control unlimited irrigation zones independently
- **Z2M Integration**: Direct control of Zigbee2MQTT water valves with sensor support
- **Beautiful Web UI**: Modern, responsive interface accessible from the Home Assistant sidebar
- **No YAML Required**: Everything configurable through the UI after initial setup
- **Smart Sensors**: Support for flow meters and soil moisture sensors
- **Water Conservation**: Track water usage and savings
- **Multiple Weather APIs**: Choose from OpenWeatherMap, WeatherAPI, or Visual Crossing

## 📦 Installation

1. **Add Repository**:
   - In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the three dots menu → **Repositories**
   - Add: `https://github.com/ttaylor0024/HA_Z2M_Smart_Irrigation`

2. **Install Add-on**:
   - Find "Smart Irrigation Controller" in the add-on store
   - Click **Install**
   - Wait for installation to complete

3. **Initial Configuration**:
   - Click **Configuration** tab
   - Enter your weather API key (see Weather API Setup below)
   - Set your location (latitude/longitude)
   - Configure at least one zone
   - Click **Save**

4. **Start the Add-on**:
   - Go to the **Info** tab
   - Click **Start**
   - Enable **Start on boot** and **Show in sidebar**

## 🌦️ Weather API Setup

### Option 1: OpenWeatherMap (Recommended)
1. Sign up at [openweathermap.org](https://openweathermap.org/api)
2. Get your free API key
3. Free tier includes 1,000 calls/day

### Option 2: WeatherAPI
1. Sign up at [weatherapi.com](https://www.weatherapi.com/)
2. Get your free API key
3. Free tier includes 1,000,000 calls/month

### Option 3: Visual Crossing
1. Sign up at [visualcrossing.com](https://www.visualcrossing.com/)
2. Get your free API key
3. Free tier includes 1,000 calls/day

## ⚙️ Configuration Options

### Basic Settings

```yaml
weather_api_key: "your_api_key_here"
weather_provider: "openweathermap"  # or "weatherapi" or "visualcrossing"
latitude: 40.7128
longitude: -74.0060
units: "metric"  # or "imperial" for inches/fahrenheit
```

### Zone Configuration

Each zone can be configured with:

- **name**: Display name for the zone
- **entity_id**: The switch entity that controls the valve (e.g., `switch.garden_valve`)
- **enabled**: Whether the zone is active
- **zone_type**: Type of irrigation (lawn, garden, drip, flowers, trees)
- **duration**: How long to water (in minutes)
- **schedule**: What time to start watering (24-hour format)
- **days**: Which days to water
- **flow_sensor**: (Optional) Entity ID of flow meter sensor
- **moisture_sensor**: (Optional) Entity ID of soil moisture sensor
- **moisture_threshold**: Skip watering if moisture is above this percentage

### Weather Settings

**Rain Forecast**:
- **enabled**: Check weather forecast before watering
- **threshold_mm**: Amount of rain that will skip irrigation
- **hours_ahead**: How far ahead to check forecast
- **skip_percentage**: Probability of rain to skip watering

**Recent Rain**:
- **enabled**: Check recent rainfall
- **threshold_mm**: Amount of recent rain to trigger action
- **hours_back**: How far back to check
- **compensation_enabled**: Reduce watering time based on recent rain
- **compensation_ratio**: How much to reduce (0.5 = 50% reduction)

## 🖥️ Using the Web Interface

### Dashboard Overview

The main dashboard shows:
- **Active Zones**: Number of enabled zones
- **Water Saved**: Amount of water conserved today
- **Next Run**: When the next irrigation will start
- **Weather Status**: Current weather decision (Normal/Skip/Reduce)

### Zone Management

Each zone card displays:
- Current status (idle, running, completed)
- Schedule and duration settings
- Last run time and water usage
- Live sensor readings (if configured)

**Zone Controls**:
- **Run**: Manually start irrigation
- **Settings**: Adjust schedule and parameters
- **Toggle**: Enable/disable the zone

### Quick Actions

Floating action buttons provide:
- **Run All**: Start all enabled zones
- **Test Mode**: Run each zone for 1 minute to test

### Weather Information

The weather section shows:
- Forecast rain amount
- Probability of precipitation
- Recent rainfall
- Current irrigation decision

## 🔧 Advanced Features

### Sensor Integration

**Flow Sensors**:
- Monitor real-time water flow
- Track total water usage per zone
- Detect potential leaks or blockages

**Moisture Sensors**:
- Skip watering when soil is already moist
- Set custom thresholds per zone
- Optimize water usage

### Zone Types

Different zone types have optimized defaults:
- **Lawn**: Standard grass areas
- **Garden**: Vegetable gardens
- **Drip**: Drip irrigation systems
- **Flowers**: Flower beds
- **Trees**: Tree watering zones

### Water Conservation

The system automatically:
- Skips watering when rain is forecast
- Reduces duration based on recent rainfall
- Tracks water saved from smart decisions
- Monitors total usage per zone

## 📊 API Endpoints

For advanced users and integrations:

- `GET /api/status` - Get full system status
- `POST /api/run_zone` - Start a specific zone
- `POST /api/run_all` - Start all zones
- `GET /api/weather_check` - Get weather conditions
- `POST /api/toggle_zone` - Enable/disable a zone
- `POST /api/update_zone` - Update zone settings

## 🚨 Troubleshooting

### Add-on Won't Start
1. Check the add-on logs for errors
2. Verify your weather API key is valid
3. Ensure at least one zone is configured
4. Check that entity IDs are correct

### Zones Not Running
1. Verify the zone is enabled
2. Check that the entity exists in Home Assistant
3. Ensure schedule time hasn't passed today
4. Review weather conditions (might be skipping)

### Weather Data Missing
1. Verify API key is correct
2. Check your API usage limits
3. Ensure latitude/longitude are correct
4. Try a different weather provider

### Sensor Issues
1. Verify sensor entity IDs are correct
2. Check sensors are reporting values
3. Ensure threshold values are reasonable
4. Check Home Assistant logs

## 💡 Tips & Best Practices

1. **Schedule Early**: Water in early morning (4-8 AM) to minimize evaporation
2. **Zone Types Matter**: Use appropriate durations for different plant types
3. **Start Conservative**: Begin with shorter durations and adjust based on results
4. **Monitor Sensors**: Regularly check sensor readings for accuracy
5. **Seasonal Adjustments**: Update schedules seasonally as weather changes
6. **Test Regularly**: Use test mode monthly to ensure all valves work
7. **Track Usage**: Monitor water consumption trends in the dashboard

## 🔐 Security & Privacy

- All data stays local to your Home Assistant instance
- Weather API calls are made directly from the add-on
- No data is sent to third parties
- API keys are stored securely in your configuration

## 📝 Example Configurations

### Basic Lawn Setup
```yaml
zones:
  - name: "Front Lawn"
    entity_id: "switch.front_lawn_valve"
    enabled: true
    zone_type: "lawn"
    duration: 20
    schedule: "06:00"
    days: ["mon", "wed", "fri"]
```

### Advanced Garden with Sensors
```yaml
zones:
  - name: "Vegetable Garden"
    entity_id: "switch.garden_valve"
    enabled: true
    zone_type: "garden"
    duration: 30
    schedule: "05:30"
    days: ["tue", "thu", "sat"]
    flow_sensor: "sensor.garden_flow_rate"
    moisture_sensor: "sensor.garden_moisture"
    moisture_threshold: 40
```

### Water-Saving Configuration
```yaml
rain_forecast:
  enabled: true
  threshold_mm: 3.0  # Skip if expecting 3mm+ rain
  hours_ahead: 24
  skip_percentage: 60  # Skip if 60%+ chance of rain
recent_rain:
  enabled: true
  threshold_mm: 5.0  # Reduce/skip if 5mm+ recent rain
  hours_back: 24
  compensation_enabled: true
  compensation_ratio: 0.7  # Reduce by up to 70%
```

## 🤝 Support

If you encounter issues:
1. Check the add-on logs first
2. Review this documentation
3. Submit issues on [GitHub](https://github.com/ttaylor0024/HA_Z2M_Smart_Irrigation)
4. Include your configuration (without API keys) when reporting

## 📄 License

This add-on is released under the MIT License. See the repository for details.

---

**Enjoy your smart, water-efficient garden! 🌱💧**
