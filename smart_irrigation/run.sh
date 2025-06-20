#!/bin/bash
set -e

echo "Starting Smart Irrigation Controller..."
cd /app
exec python3 -u main.py
