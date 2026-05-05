#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# remote-claude-openclaw start.sh
# Starts OpenClaw gateway with WhatsApp transport.
# OpenClaw handles: WhatsApp ↔ Claude Code ↔ Reply
# Safety rules are in OpenClaw workspace CLAUDE.md
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

# ── Identity banner ───────────────────────────
echo "┌─────────────────────────────────────────────┐"
echo "│  AGENT IDENTITY                             │"
echo "│                                             │"
echo "│  Owner:  ${FOUNDER_NAME} (${FOUNDER_ROLE})"
echo "│  Repo:   ${LOCAL_REPO_PATH}"
echo "│  Channel: ${CHANNEL:-whatsapp}"
echo "│  Proxy:   ${ANTHROPIC_BASE_URL:-http://localhost:8082}"
echo "│                                             │"
echo "│  Transport: OpenClaw (WhatsApp)             │"
echo "│  Runner:   Claude Code CLI                  │"
echo "│  Safety:   OpenClaw workspace CLAUDE.md     │"
echo "│                                             │"
echo "│  SAFETY MODE: ENABLED                       │"
echo "│  - No push without explicit 'push' command  │"
echo "│  - No operations outside LOCAL_REPO_PATH    │"
echo "│  - No destructive commands                  │"
echo "│  - All commands logged                      │"
echo "│  - Unknown senders rejected                 │"
echo "└─────────────────────────────────────────────┘"
echo ""

# ── Verify workspace has safety rules ─────────
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
if [ ! -f "$WORKSPACE/CLAUDE.md" ]; then
  echo "[setup] Installing safety rules to OpenClaw workspace..."
  cp "$ROOT_DIR/skills/remote-claude-code/CLAUDE.md" "$WORKSPACE/CLAUDE.md"
fi

# ── Start OpenClaw gateway ───────────────────
echo "[start] Launching OpenClaw gateway..."
echo "[start] WhatsApp channel: ${CHANNEL:-whatsapp}"
echo "[start] Allowlisted senders: ${ALLOWED_SENDERS}"
echo ""

# OpenClaw reads its own config from ~/.openclaw/openclaw.json
# The workspace CLAUDE.md provides safety rules to the agent
# The WhatsApp plugin handles message transport

openclaw gateway \
  --port "${OPENCLAW_PORT:-18789}" \
  --bind loopback \
  --auth token \
  --token "${OPENCLAW_GATEWAY_TOKEN:-}" \
  --verbose &

GATEWAY_PID=$!
echo "$GATEWAY_PID" > "$ROOT_DIR/.agent.pid"

echo "[start] OpenClaw gateway running (PID $GATEWAY_PID)"
echo "[start] Send a WhatsApp message to test."
echo "[start] Stop: ./scripts/stop.sh"
echo "[start] Logs: openclaw logs"
echo ""
