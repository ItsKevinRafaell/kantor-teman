#!/bin/bash
# Fix all missing imports across routers

set -e

ROUTERS="/home/qqwtlphb/backend/routers"
NEW_CODE="/tmp/kantor-teman-main/backend/routers"

# Copy all latest routers from fresh download
cp -f $NEW_CODE/*.py $ROUTERS/

# Verify no permission issues, fix if needed
chmod 644 $ROUTERS/*.py 2>/dev/null || true

# Reload app
touch /home/qqwtlphb/backend/tmp/restart.txt 2>/dev/null || touch /home/qqwtlphb/backend/passenger_wsgi.py

echo "Done - app restarted"
