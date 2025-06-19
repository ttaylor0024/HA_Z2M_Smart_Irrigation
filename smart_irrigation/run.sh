#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

echo "Starting Smart Irrigation Controller..."

# Check if config exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: Configuration file not found at $CONFIG_PATH!"
    exit 1
fi

# Display configuration
echo "Configuration loaded from $CONFIG_PATH"

# Change to app directory
cd /app

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Start the application with proper error handling
echo "Starting irrigation controller..."
exec python3 -u main.py 2>&1 | tee /app/logs/irrigation.log
