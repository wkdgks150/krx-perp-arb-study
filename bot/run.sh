#!/bin/bash
# Gap FADE Bot — daily runner
# Called by cron or manually

DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/bot.log"
PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "────────────────────────────────────" >> "$LOG"
echo "[$(date)] Running: $1" >> "$LOG"

cd "$DIR" && $PYTHON main.py "$1" >> "$LOG" 2>&1

echo "[$(date)] Done: $1" >> "$LOG"
