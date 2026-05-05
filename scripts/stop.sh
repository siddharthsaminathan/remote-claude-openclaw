#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "══════════════════════════════════════════════"
echo "  remote-claude-openclaw — stop"
echo "══════════════════════════════════════════════"
echo ""

# Kill OpenClaw gateway
if [ -f "$ROOT_DIR/.agent.pid" ]; then
  PID=$(cat "$ROOT_DIR/.agent.pid")
  if kill -0 "$PID" 2>/dev/null; then
    echo "[stop] Stopping OpenClaw gateway (PID $PID)..."
    kill "$PID" 2>/dev/null || true
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
      echo "[stop] Force killing..."
      kill -9 "$PID" 2>/dev/null || true
    fi
    echo "[stop] Gateway stopped."
  else
    echo "[stop] Gateway (PID $PID) is not running."
  fi
  rm -f "$ROOT_DIR/.agent.pid"
else
  echo "[stop] No PID file found."
fi

# Kill any lingering openclaw processes
PIDS=$(pgrep -f "openclaw gateway" 2>/dev/null || true)
if [ -n "$PIDS" ]; then
  echo "[stop] Found lingering openclaw processes: $PIDS"
  echo "$PIDS" | xargs kill 2>/dev/null || true
fi

echo ""
