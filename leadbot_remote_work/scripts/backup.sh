#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/leadbot/backups"
mkdir -p $BACKUP_DIR

# Database backup
PGPASSWORD=leadbot_pass_2024 pg_dump -h localhost -U leadbot leadbot_db > $BACKUP_DIR/leadbot_$DATE.sql

# Compress
gzip $BACKUP_DIR/leadbot_$DATE.sql

# Keep last 7 days
find $BACKUP_DIR -name 'leadbot_*.sql.gz' -mtime +7 -delete

# Log
echo "[$(date)] Backup completed: leadbot_$DATE.sql.gz" >> /var/log/leadbot-backup.log

# Notify on failure
if [ $? -ne 0 ]; then
  echo "[$(date)] Backup FAILED" >> /var/log/leadbot-backup.log
fi
