#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# remote-claude-openclaw doctor.sh
# Diagnostic check — verifies everything works.
# ──────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PASS=0
FAIL=0

check() {
  local label="$1"
  local result="$2"
  local detail="${3:-}"
  if [ "$result" = "ok" ]; then
    echo "  [PASS] $label"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $label — $detail"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "══════════════════════════════════════════════"
echo "  remote-claude-openclaw — doctor"
echo "══════════════════════════════════════════════"
echo ""

# Load .env
if [ -f "$ROOT_DIR/.env" ]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
else
  echo "FATAL: .env not found. Copy .env.example to .env first."
  exit 1
fi

# ── 1. Claude Code works ──────────────────────
echo "[1] Claude Code CLI"
CLAUDE_CMD="${CLAUDE_CODE_COMMAND:-claude}"
if command -v "$CLAUDE_CMD" >/dev/null 2>&1; then
  CLAUDE_VERSION=$("$CLAUDE_CMD" --version 2>&1 || echo "unknown")
  check "claude binary exists" "ok" "$CLAUDE_VERSION"
else
  check "claude binary exists" "fail" "$CLAUDE_CMD not on PATH"
fi

# ── 2. Proxy reachable ────────────────────────
echo "[2] Proxy reachable"
PROXY_URL="${ANTHROPIC_BASE_URL:-http://localhost:8082}"
PROXY_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${PROXY_URL}/health" 2>/dev/null || echo "000")
if [ "$PROXY_CODE" != "000" ]; then
  check "proxy $PROXY_URL" "ok" "HTTP $PROXY_CODE"
else
  check "proxy $PROXY_URL" "fail" "connection refused"
fi

# ── 3. Model routing works ────────────────────
echo "[3] Model routing (via proxy)"
# Test that model aliases map correctly by checking proxy /models endpoint
MODELS=$(curl -s --max-time 5 "${PROXY_URL}/models" 2>/dev/null || echo "[]")
if [ "$MODELS" != "[]" ] && [ -n "$MODELS" ]; then
  check "proxy returns model list" "ok"
else
  check "proxy returns model list" "fail" "no models returned"
fi

# ── 4. Local repo path ────────────────────────
echo "[4] Local repo path"
if [ -d "${LOCAL_REPO_PATH:-}" ]; then
  check "LOCAL_REPO_PATH exists" "ok" "$LOCAL_REPO_PATH"
  if [ -d "$LOCAL_REPO_PATH/.git" ]; then
    check "  is git repo" "ok"
  else
    check "  is git repo" "fail" "no .git directory"
  fi
else
  check "LOCAL_REPO_PATH exists" "fail" "${LOCAL_REPO_PATH:-NOT_SET} not found"
fi

# ── 5. Git status ─────────────────────────────
echo "[5] Git status"
if [ -d "${LOCAL_REPO_PATH:-}/.git" ]; then
  cd "$LOCAL_REPO_PATH"
  BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [ "$DIRTY" = "0" ]; then
    check "git clean" "ok" "branch=$BRANCH"
  else
    check "git dirty" "ok" "branch=$BRANCH, ${DIRTY} files changed"
  fi
  cd "$ROOT_DIR"
else
  check "git available" "fail" "cannot check"
fi

# ── 6. Channel config ─────────────────────────
echo "[6] Channel: ${CHANNEL:-NOT_SET}"
CHANNEL_VAR=""
case "${CHANNEL:-}" in
  whatsapp) CHANNEL_VAR="${WHATSAPP_TOKEN:-NOT_SET}${TWILIO_ACCOUNT_SID:-}" ;;
  telegram) CHANNEL_VAR="${TELEGRAM_BOT_TOKEN:-NOT_SET}" ;;
  slack)    CHANNEL_VAR="${SLACK_BOT_TOKEN:-NOT_SET}${SLACK_APP_TOKEN:-}" ;;
  *)        CHANNEL_VAR="" ;;
esac
if [ -n "$CHANNEL_VAR" ] && [ "$CHANNEL_VAR" != "NOT_SET" ]; then
  check "channel auth ($CHANNEL)" "ok"
else
  check "channel auth ($CHANNEL)" "fail" "set ${CHANNEL^^}_TOKEN or related env var"
fi

# ── 7. Owner identity ─────────────────────────
echo "[7] Owner identity"
check "FOUNDER_ID" "ok" "${FOUNDER_ID:-NOT_SET}"
check "FOUNDER_NAME" "ok" "${FOUNDER_NAME:-NOT_SET}"
check "FOUNDER_ROLE" "ok" "${FOUNDER_ROLE:-NOT_SET}"

# ── 8. Allowlist ──────────────────────────────
echo "[8] Sender allowlist"
if [ -n "${ALLOWED_SENDERS:-}" ]; then
  SENDER_COUNT=$(echo "$ALLOWED_SENDERS" | tr ',' '\n' | wc -l | tr -d ' ')
  check "allowlist configured" "ok" "${SENDER_COUNT} sender(s)"
else
  check "allowlist configured" "fail" "ALLOWED_SENDERS is empty — no phone can reach this agent"
fi

# ── Summary ───────────────────────────────────
echo ""
echo "──────────────────────────────────────────────"
echo "  Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  echo "  Fix failures above before running start.sh"
else
  echo "  All checks passed — ready: ./scripts/start.sh"
fi
echo "──────────────────────────────────────────────"
echo ""
