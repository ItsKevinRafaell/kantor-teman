#!/usr/bin/env bash
# Warm-up ping for kantorteman backend on shared hosting.
#
# LiteSpeed LSAPI workers spin down after a period of inactivity. The first
# request after spin-down has to respawn the Python process, which on a busy
# shared node can take 5–20s — long enough for the browser to give up with
# ERR_TIMED_OUT / "Failed to fetch".
#
# Hitting /api/health every couple of minutes keeps the worker warm.
# /api/health intentionally does no DB work, so it only keeps the process
# responsive without holding DB connections.
#
# Install on the PRODUCTION server (cPanel → Cron Jobs), NOT your laptop:
#   */2 * * * * /home/qqwtlphb/scripts/warmup.sh >> /home/qqwtlphb/backend/warmup.log 2>&1
#
# Run locally to check if the API is up:
#   bash scripts/warmup.sh

set -u
URL="${KT_HEALTH_URL:-https://api.kantorteman.my.id/api/health}"

resp=$(curl -sS -m 10 -o /dev/null -w "%{http_code} %{time_total}" "$URL" 2>/dev/null) || resp="000 0.000"
echo "$(date '+%F %T')  $resp  $URL"
