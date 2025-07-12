#!/bin/bash

# Jarvis BriefMe Daily Execution Script
# This script runs the daily briefing generation and email

# Set timezone for Arizona
export TZ="America/Phoenix"

# Navigate to project directory
cd "/Users/garrettsullivan/Desktop/AUTOMATE/Vibe Code/Jarvis_BriefMe"

# Create timestamp
TIMESTAMP=$(date "+%Y-%m-%d_%H-%M-%S")
LOG_FILE="logs/daily_$TIMESTAMP.log"

# Log start
echo "[$TIMESTAMP] Starting Jarvis Daily Briefing" >> "$LOG_FILE"
echo "[$TIMESTAMP] Current time: $(date)" >> "$LOG_FILE"

# Activate virtual environment and run with email
. venv/bin/activate && python3 -m src.main --email >> "$LOG_FILE" 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] ✅ Daily briefing completed successfully" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] ❌ Daily briefing failed with exit code $?" >> "$LOG_FILE"
fi

# Keep only last 30 log files
find logs/ -name "daily_*.log" -type f | sort | head -n -30 | xargs rm -f

echo "[$TIMESTAMP] Daily briefing execution finished" >> "$LOG_FILE"
