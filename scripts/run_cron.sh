#!/bin/bash
# Shell wrapper script for remote Linux crontab execution of nxt.bargains pipeline

# Resolve project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory if missing
mkdir -p "$SCRIPT_DIR/logs"

# Activate Virtual Environment if present
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
echo "==================================================" >> "$SCRIPT_DIR/logs/cron.log"
echo "[$TIMESTAMP] Starting Remote Server Daily Deals Ingestion" >> "$SCRIPT_DIR/logs/cron.log"
echo "==================================================" >> "$SCRIPT_DIR/logs/cron.log"

# Run Production Pipeline
python run_nxt_bargains_pipeline.py >> "$SCRIPT_DIR/logs/cron.log" 2>&1

EXIT_CODE=$?
TIMESTAMP_END=$(date "+%Y-%m-%d %H:%M:%S")
echo "[$TIMESTAMP_END] Pipeline Run Finished with Exit Code $EXIT_CODE" >> "$SCRIPT_DIR/logs/cron.log"
echo "" >> "$SCRIPT_DIR/logs/cron.log"
