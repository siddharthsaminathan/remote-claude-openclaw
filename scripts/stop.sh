#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# remote-claude-openclaw stop.sh
# Gracefully stops the local agent.
# ──────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "══════════════════════════════════════════════"
echo "  remote-claude-openclaw — stop"
echo "══════════════════════════════════════════════"
echo ""

if [ -f "$ROOT_DIR/.agent.pid" ]; then
  PID=$(cat "$ROOT_DIR/.agent.pid")
  if kill -0 "$PID" 2>/dev/null; then
    echo "[stop] Sending SIGTERM to agent (PID $PID)..."
    kill "$PID" 2>/dev/null || true
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
      echo "[stop] Agent didn't stop — sending SIGKILL..."
      kill -9 "$PID" 2>/dev/null || true
    fi
    echo "[stop] Agent stopped."
  else
    echo "[stop] Agent (PID $PID) is not running."
  fi
  rm -f "$ROOT_DIR/.agent.pid"
else
  echo "[stop] No agent PID file found."
  # Find and kill any lingering agent processes
  PIDS=$(pgrep -f "skills/remote-claude-code/agent.py" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "[stop] Found lingering agent processes: $PIDS"
    echo "$PIDS" | xargs kill 2>/dev/null || true
    echo "[stop] Killed lingering processes."
  fi
fi

echo ""
