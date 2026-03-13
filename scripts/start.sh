#!/bin/bash
# Startup script for browser orchestrator with external CDP browser
# Part 8 - Final Startup Flow

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Browser Orchestrator Startup"
echo "=========================================="

# Step 1: Check if browser is already running
echo "[1/5] Checking for existing browser..."
if curl -s http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
    echo "  ✅ Browser already running on CDP port 9222"
    BROWSER_WAS_RUNNING=true
else
    echo "  ℹ️  No browser found, launching new instance..."
    ./scripts/launch_browser.sh
    BROWSER_WAS_RUNNING=false
fi

# Step 2: Verify CDP endpoint
echo "[2/5] Verifying CDP endpoint..."
CDP_RESPONSE=$(curl -s http://127.0.0.1:9222/json/version)
if echo "$CDP_RESPONSE" | grep -q "webSocketDebuggerUrl"; then
    BROWSER_VERSION=$(echo "$CDP_RESPONSE" | grep -o '"Browser": "[^"]*"' | cut -d'"' -f4)
    echo "  ✅ CDP ready: $BROWSER_VERSION"
else
    echo "  ❌ CDP endpoint not responding correctly"
    exit 1
fi

# Step 3: Run health check
echo "[3/5] Running health checks..."
if python3 scripts/health_check.py > /dev/null 2>&1; then
    echo "  ✅ Health checks PASSED"
else
    echo "  ⚠️  Health checks had warnings (continuing anyway)"
fi

# Step 4: Initialize router
echo "[4/5] Initializing browser router..."
export CDP_URL="http://127.0.0.1:9222"
export USE_EXTERNAL_BROWSER="true"
echo "  ℹ️  CDP_URL=$CDP_URL"
echo "  ℹ️  USE_EXTERNAL_BROWSER=$USE_EXTERNAL_BROWSER"

# Step 5: Start the application (or just confirm ready)
echo "[5/5] Startup complete!"
echo "=========================================="
echo "Browser stack is ready:"
echo "  - External Chromium: localhost:9222"
echo "  - browser-use: will connect via CDP"
echo "  - Playwright: can connect via CDP"
echo ""
echo "To start the API server, run:"
echo "  cd $SCRIPT_DIR && uvicorn adapter.app:app --reload"
echo "=========================================="
