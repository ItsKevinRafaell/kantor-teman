#!/bin/bash
# Performance Optimization Deployment Script
# Run this on the production server

set -e  # Exit on error

echo "=== Kantor Teman Performance Optimization Deployment ==="
echo ""

# Backup current code
echo "1. Creating backup..."
cp main.py main.py.backup.$(date +%Y%m%d_%H%M%S)

# Check database type
if grep -q "sqlite" .env 2>/dev/null || [ ! -f .env ]; then
    echo "SQLite detected - indexes will be added via SQLAlchemy"
    DB_TYPE="sqlite"
else
    DB_TYPE="postgres"
fi

# Apply database indexes
if [ "$DB_TYPE" = "postgres" ]; then
    echo ""
    echo "2. Applying database indexes..."

    # Load DATABASE_URL from .env
    export $(grep -v '^#' .env | xargs)

    if [ -z "$DATABASE_URL" ]; then
        echo "ERROR: DATABASE_URL not found in .env"
        exit 1
    fi

    echo "Running index migration..."
    psql "$DATABASE_URL" < add_performance_indexes.sql

    if [ $? -eq 0 ]; then
        echo "✓ Indexes created successfully"
    else
        echo "ERROR: Index creation failed"
        exit 1
    fi
else
    echo "2. Skipping PostgreSQL indexes (SQLite in use)"
fi

# Restart the application
echo ""
echo "3. Restarting application..."

# Kill existing process
pkill -f "uvicorn main:app" || pkill -f "python.*main.py" || true
sleep 2

# Start new process
if [ -f "start_dev.sh" ]; then
    nohup bash start_dev.sh > app.log 2>&1 &
elif [ -f "passenger_wsgi.py" ]; then
    touch tmp/restart.txt  # Passenger restart
    echo "✓ Passenger restart triggered"
else
    nohup python main.py > app.log 2>&1 &
fi

sleep 3

# Verify
echo ""
echo "4. Verifying deployment..."

if pgrep -f "uvicorn\|python.*main" > /dev/null; then
    echo "✓ Application is running"
else
    echo "⚠ Application may not be running - check app.log"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Monitor logs: tail -f app.log"
echo "2. Test performance: curl -w '%{time_total}' http://localhost:8000/api/proposals"
echo "3. Check slow queries in logs for X-Process-Time headers"
echo ""
echo "Expected improvements:"
echo "  - /api/proposals: 3-5s → 200-400ms (10-15x faster)"
echo "  - /api/proposals/analytics/all: 5-10s → 300-500ms (15-20x faster)"
echo ""
