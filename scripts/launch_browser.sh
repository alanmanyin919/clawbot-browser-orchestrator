#!/bin/bash
# Browser Launcher - External Chromium with CDP
# Part 2 of browser automation fix

set -e

CDP_PORT=9222
USER_DATA_DIR="/tmp/clawbot-browser"

# Kill existing browser on this port if running
pkill -f "remote-debugging-port=$CDP_PORT" 2>/dev/null || true
sleep 1

# Launch Chromium with safe flags
google-chrome \
    --remote-debugging-port=$CDP_PORT \
    --user-data-dir=$USER_DATA_DIR \
    --no-first-run \
    --no-default-browser-check \
    --disable-dev-shm-usage \
    --disable-background-networking \
    --disable-extensions \
    --disable-gpu \
    --no-proxy-server \
    --headless=new \
    --no-sandbox \
    --disable-automation \
    --disable-blink-features=AutomationControlled \
    about:blank &

BROWSER_PID=$!

echo "Browser launched with PID: $BROWSER_PID"
echo "CDP port: $CDP_PORT"

# Wait for CDP to be ready
echo "Waiting for CDP to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:$CDP_PORT/json/version > /dev/null 2>&1; then
        echo "CDP is ready!"
        curl -s http://127.0.0.1:$CDP_PORT/json/version
        exit 0
    fi
    sleep 1
done

echo "ERROR: CDP did not become ready in time"
exit 1
