#!/usr/bin/with-contenv bashio

# Get configuration
CONFIG_PATH=/data/options.json

# Validate configuration
if ! bashio::config.exists 'weather_api_key'; then
    bashio::log.fatal "Weather API key is required!"
    exit 1
fi

if ! bashio::config.exists 'latitude' || ! bashio::config.exists 'longitude'; then
    bashio::log.fatal "Latitude and longitude are required!"
    exit 1
fi

# Log configuration (without sensitive data)
bashio::log.info "Starting Smart Irrigation Controller..."
bashio::log.info "Weather Provider: $(bashio::config 'weather_provider')"
bashio::log.info "Number of zones: $(bashio::config 'zones | length')"

# Export Home Assistant token
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-$(bashio::config 'supervisor_token')}"

# Change to app directory
cd /app

# Start the application
bashio::log.info "Starting irrigation controller..."
exec python3 main.py
