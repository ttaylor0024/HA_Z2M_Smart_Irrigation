#!/usr/bin/with-contenv bashio

echo "Starting Smart Irrigation Controller..."
cd /app
exec python3 -u main.py
