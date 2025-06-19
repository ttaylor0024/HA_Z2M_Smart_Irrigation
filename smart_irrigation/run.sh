#!/bin/sh
set -e

CONFIG_PATH=/data/options.json

echo "Starting Smart Irrigation Controller..."

if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: Configuration file not found!"
    exit 1
fi

echo "Configuration loaded"
cd /app
mkdir -p /app/logs
echo "Starting irrigation controller..."
exec python3 -u main.py 2>&1 | tee /app/logs/irrigation.log
