#!/usr/bin/env bashio

bashio::log.info "Starting Smart Irrigation Controller..."
cd /app
exec python3 -u main.py
