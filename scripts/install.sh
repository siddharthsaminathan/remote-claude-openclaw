#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# remote-claude-openclaw install.sh
# Idempotent. Run on each founder's laptop.
# ──────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "══════════════════════════════════════════════"
echo "  remote-claude-openclaw — install"
echo "══════════════════════════════════════════════"
echo ""

# ── 1. Check prerequisites ────────────────────
echo "[1/7] Checking prerequisites..."

fail() { echo "  FAIL: $1"; exit 1; }
ok()   { echo "  OK:   $1"; }

command -v node   >/dev/null 2>&1 && ok "node $(node --version)"   || fail "node not found — install Node.js >= 18"
command -v python3 >/dev/null 2>&1 && ok "python3 $(python3 --version 2>&1 | cut -d' ' -f2)" || fail "python3 not found"
command -v git     >/dev/null 2>&1 && ok "git $(git --version | cut -d' ' -f3)" || fail "git not found"

# ── 2. Check Claude Code ──────────────────────
echo ""
echo "[2/7] Checking Claude Code..."

if command -v claude >/dev/null 2>&1; then
  ok "claude CLI found at $(command -v claude)"
else
  fail "claude CLI not found — install via: npm install -g @anthropic-ai/claude-code"
fi

# ── 3. Check .env ─────────────────────────────
echo ""
echo "[3/7] Checking .env..."

if [ -f "$ROOT_DIR/.env" ]; then
  ok ".env exists"
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
else
  echo "  WARN: .env not found — copying from .env.example"
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "  ACTION REQUIRED: edit $ROOT_DIR/.env with your details, then re-run install.sh"
  exit 0
fi

# ── 4. Check proxy reachable ──────────────────
echo ""
echo "[4/7] Checking proxy at ${ANTHROPIC_BASE_URL:-http://localhost:8082}..."

PROXY_URL="${ANTHROPIC_BASE_URL:-http://localhost:8082}"
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${PROXY_URL}/health" 2>/dev/null | grep -q "200\|404\|401"; then
  ok "proxy reachable at $PROXY_URL"
else
  echo "  WARN: proxy not reachable at $PROXY_URL (continuing anyway)"
fi

# ── 5. Check repo path ────────────────────────
echo ""
echo "[5/7] Checking repo at ${LOCAL_REPO_PATH:-NOT_SET}..."

if [ "${LOCAL_REPO_PATH:-}" = "" ]; then
  fail "LOCAL_REPO_PATH not set in .env"
fi

if [ -d "$LOCAL_REPO_PATH" ]; then
  ok "repo exists at $LOCAL_REPO_PATH"
  if [ -d "$LOCAL_REPO_PATH/.git" ]; then
    ok "  -> is a git repository"
  else
    echo "  WARN: not a git repository (continuing anyway)"
  fi
else
  fail "repo not found at $LOCAL_REPO_PATH — check LOCAL_REPO_PATH in .env"
fi

# ── 6. Install OpenClaw dependencies ──────────
echo ""
echo "[6/7] Installing OpenClaw dependencies..."

# OpenClaw is the channel bridge (WhatsApp/Telegram/Slack)
# It needs to be installed on this laptop
if [ -d "$ROOT_DIR/openclaw" ]; then
  ok "OpenClaw directory exists"
  cd "$ROOT_DIR/openclaw"
  npm install --silent 2>/dev/null || echo "  WARN: npm install had issues (may be fine)"
  cd "$ROOT_DIR"
else
  echo "  INFO: OpenClaw not bundled — will use python bridge"
  pip3 install aiohttp websockets 2>/dev/null || echo "  WARN: pip install had issues"
fi

# ── 7. Create local config from examples ──────
echo ""
echo "[7/7] Creating local config..."

if [ ! -f "$ROOT_DIR/config/founders.json" ]; then
  cp "$ROOT_DIR/config/founders.example.json" "$ROOT_DIR/config/founders.json"
  ok "config/founders.json created from example"
else
  ok "config/founders.json already exists"
fi

if [ ! -f "$ROOT_DIR/config/agent.json" ]; then
  cp "$ROOT_DIR/config/agent.example.json" "$ROOT_DIR/config/agent.json"
  ok "config/agent.json created from example"
else
  ok "config/agent.json already exists"
fi

# ── Done ──────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  Install complete!"
echo ""
echo "  Owner:  ${FOUNDER_NAME:-UNKNOWN} (${FOUNDER_ROLE:-UNKNOWN})"
echo "  Repo:   ${LOCAL_REPO_PATH:-UNSET}"
echo "  Channel: ${CHANNEL:-UNSET}"
echo ""
echo "  Next: ./scripts/doctor.sh"
echo "══════════════════════════════════════════════"
echo ""
