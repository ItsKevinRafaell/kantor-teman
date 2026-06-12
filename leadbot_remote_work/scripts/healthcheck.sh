#!/bin/bash
LOG="/var/log/leadbot-health.log"

# Check API
if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
  echo "[$(date)] OK" >> $LOG
else
  echo "[$(date)] API DOWN - restarting" >> $LOG
  pm2 restart leadbot
fi

# Check disk
DISK_USAGE=$(df /opt/leadbot | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
  echo "[$(date)] DISK WARNING: ${DISK_USAGE}%" >> $LOG
fi
