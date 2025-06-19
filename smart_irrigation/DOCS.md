# Home Assistant Add-on: Smart Irrigation Controller

Automated irrigation system with weather integration and Z2M valve control.

## About

This add-on provides intelligent irrigation control for your Home Assistant setup. It integrates with weather services to make smart decisions about when to water your garden, lawn, or crops.

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the Smart Irrigation Controller add-on
3. Configure your settings (see Configuration section)
4. Start the add-on

## Configuration

```yaml
weather_api_key: "your_api_key_here"
weather_provider: "openweathermap"
latitude: 40.7128
longitude: -74.0060
zones:
  - name: "Front Yard"
    entity_id: "switch.front_yard_valve"
    duration: 15
    schedule: "06:00"
    days: ["mon", "wed", "fri"]
rain_forecast:
  enabled: true
  threshold_mm: 5.0
  hours_ahead: 24
  skip_percentage: 80
recent_rain:
  enabled: true
  threshold_mm: 2.0
  hours_back: 24
  compensation_enabled: true
  compensation_ratio: 0.5