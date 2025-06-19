#!/bin/bash
set -e

echo "Starting Smart Irrigation Controller..."

# Check if config exists
if [ ! -f /data/options.json ]; then
    echo "ERROR: Configuration file not found!"
    exit 1
fi

# Change to app directory
cd /app

# Start the application
echo "Starting Python application..."
exec python3 main.py
