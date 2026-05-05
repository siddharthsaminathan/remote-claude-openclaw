#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# remote-claude-openclaw start.sh
# Starts the phone-controlled local agent.
# ──────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "══════════════════════════════════════════════"
echo "  remote-claude-openclaw — start"
echo "══════════════════════════════════════════════"
echo ""

# Load .env
if [ -f "$ROOT_DIR/.env" ]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
else
  echo "FATAL: .env not found. Run install.sh first."
  exit 1
fi

# ── Safety checks ─────────────────────────────
echo "[safety] Sandbox: LOCAL_REPO_PATH=${LOCAL_REPO_PATH}"
echo "[safety] Push confirmation required: ${REQUIRE_PUSH_CONFIRMATION:-true}"
echo "[safety] Destructive command block: ${ENFORCE_REPO_SANDBOX:-true}"
echo "[safety] Command logging: ${LOG_ALL_COMMANDS:-true}"
echo ""

# ── Identity banner ───────────────────────────
echo "┌─────────────────────────────────────────────┐"
echo "│  AGENT IDENTITY                             │"
echo "│                                             │"
echo "│  Owner:  ${FOUNDER_NAME} (${FOUNDER_ROLE})"
echo "│  Repo:   ${LOCAL_REPO_PATH}"
echo "│  Channel: ${CHANNEL}"
echo "│  Model:   ${MAIN_MODEL_ALIAS} / ${CHEAP_MODEL_ALIAS}"
echo "│  Proxy:   ${ANTHROPIC_BASE_URL}"
echo "│                                             │"
echo "│  SAFETY MODE: ENABLED                       │"
echo "│  - No push without explicit approval        │"
echo "│  - No operations outside LOCAL_REPO_PATH    │"
echo "│  - No destructive commands                  │"
echo "│  - All commands logged                      │"
echo "│  - Unknown senders rejected                 │"
echo "└─────────────────────────────────────────────┘"
echo ""

# ── Kill any existing agent ───────────────────
if [ -f "$ROOT_DIR/.agent.pid" ]; then
  OLD_PID=$(cat "$ROOT_DIR/.agent.pid")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[stop] Killing previous agent (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$ROOT_DIR/.agent.pid"
fi

# ── Start agent ───────────────────────────────
LOG_FILE="$ROOT_DIR/logs/agent-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$ROOT_DIR/logs"

echo "[start] Launching remote-claude-code agent..."
echo "[start] Log: $LOG_FILE"
echo ""

# The agent is a Python process that bridges the channel → Claude Code
nohup python3 "$ROOT_DIR/skills/remote-claude-code/agent.py" \
  --env "$ROOT_DIR/.env" \
  --config "$ROOT_DIR/config/agent.json" \
  --founders "$ROOT_DIR/config/founders.json" \
  >> "$LOG_FILE" 2>&1 &

AGENT_PID=$!
echo "$AGENT_PID" > "$ROOT_DIR/.agent.pid"

echo "[start] Agent running (PID $AGENT_PID)"
echo "[start] Send a message via ${CHANNEL} to test."
echo "[start] Stop: ./scripts/stop.sh"
echo ""
