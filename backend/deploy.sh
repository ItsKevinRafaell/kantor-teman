#!/bin/bash
# Auto-deploy script for Kantorteman Backend
# Usage: bash deploy.sh

set -e

# Resolve python interpreter (server only has python3, not python)
PY="$(command -v python3 || command -v python || echo python3)"

echo "=== Kantorteman Deploy ==="
echo "Pulling latest code..."
git pull origin main

# Protect critical files - never overwrite
git checkout -- .env passenger_wsgi.py .env.production 2>/dev/null || true

echo "Running migrations (interpreter: $PY)..."
# Migration must NOT abort the deploy: restart has to run even if migrate fails.
"$PY" migrate.py || echo "WARN: migrate.py failed (continuing to restart anyway)"

echo "Restarting app..."
mkdir -p tmp
touch tmp/restart.txt 2>/dev/null || true
touch passenger_wsgi.py 2>/dev/null || true

echo "=== Done ==="
