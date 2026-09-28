#!/bin/bash
while true; do
    if ! pgrep -f "smm_server.py" > /dev/null; then
        echo "[$(date)] Starting smm_server.py..."
        python3 /app/applet/smm_server.py >> /app/applet/server.log 2>&1
    fi
    sleep 5
done
