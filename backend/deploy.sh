#!/bin/bash
# Auto-deploy script for Kantorteman Backend
# Usage: bash deploy.sh

set -e

echo "=== Kantorteman Deploy ==="
echo "Pulling latest code..."
git pull origin main

# Protect critical files - never overwrite
git checkout -- .env passenger_wsgi.py .env.production 2>/dev/null || true

echo "Running migrations..."
python migrate.py

echo "Restarting app..."
touch tmp/restart.txt 2>/dev/null || touch passenger_wsgi.py

echo "=== Done ==="