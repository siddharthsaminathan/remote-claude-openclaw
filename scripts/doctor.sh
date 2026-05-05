#!/usr/bin/env bash
set -euo pipefail

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

# ── 1. OpenClaw installed ─────────────────────
echo "[1] OpenClaw binary"
if command -v openclaw >/dev/null 2>&1; then
  OC_VERSION=$(openclaw --version 2>&1 | head -1)
  check "openclaw installed" "ok" "$OC_VERSION"
else
  check "openclaw installed" "fail" "not on PATH"
fi

# ── 2. OpenClaw config valid ─────────────────
echo "[2] OpenClaw config"
OC_CONFIG="${HOME}/.openclaw/openclaw.json"
if [ -f "$OC_CONFIG" ]; then
  check "config exists" "ok" "$OC_CONFIG"
  if python3 -c "import json; json.load(open('$OC_CONFIG'))" 2>/dev/null; then
    check "config valid JSON" "ok"
  else
    check "config valid JSON" "fail" "invalid JSON"
  fi
else
  check "config exists" "fail" "run: openclaw configure"
fi

# ── 3. WhatsApp configured ────────────────────
echo "[3] WhatsApp channel"
WHATSAPP_ENABLED=$(python3 -c "
import json
c = json.load(open('$OC_CONFIG'))
print(c.get('channels',{}).get('whatsapp',{}).get('enabled', False))
" 2>/dev/null || echo "False")
if [ "$WHATSAPP_ENABLED" = "True" ]; then
  check "whatsapp enabled" "ok"
else
  check "whatsapp enabled" "fail" "run: openclaw configure --section channels"
fi

# ── 4. Allowlist ─────────────────────────────
echo "[4] Sender allowlist"
ALLOWED=$(python3 -c "
import json
c = json.load(open('$OC_CONFIG'))
print(','.join(c.get('channels',{}).get('whatsapp',{}).get('allowFrom',[])))
" 2>/dev/null || echo "")
if [ -n "$ALLOWED" ]; then
  check "allowlist" "ok" "$ALLOWED"
else
  check "allowlist" "fail" "no senders in allowFrom"
fi

# ── 5. Safety rules in workspace ─────────────
echo "[5] Safety rules (CLAUDE.md)"
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
if [ -f "$WORKSPACE/CLAUDE.md" ]; then
  check "workspace CLAUDE.md" "ok" "$WORKSPACE/CLAUDE.md"
else
  check "workspace CLAUDE.md" "fail" "not found — safety rules missing"
fi

# ── 6. Local repo ────────────────────────────
echo "[6] Local repo"
if [ -d "${LOCAL_REPO_PATH:-}" ]; then
  check "repo exists" "ok" "$LOCAL_REPO_PATH"
  if [ -d "$LOCAL_REPO_PATH/.git" ]; then
    BRANCH=$(git -C "$LOCAL_REPO_PATH" branch --show-current 2>/dev/null || echo "?")
    DIRTY=$(git -C "$LOCAL_REPO_PATH" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    check "git repo" "ok" "branch=$BRANCH, $DIRTY dirty files"
  else
    check "git repo" "fail" "not a git repository"
  fi
else
  check "repo exists" "fail" "${LOCAL_REPO_PATH:-NOT_SET}"
fi

# ── 7. Claude Code CLI ───────────────────────
echo "[7] Claude Code CLI"
if command -v claude >/dev/null 2>&1; then
  CC_VERSION=$(claude --version 2>&1 || echo "installed")
  check "claude CLI" "ok" "$CC_VERSION"
else
  check "claude CLI" "fail" "not on PATH"
fi

# ── 8. Proxy reachable ───────────────────────
echo "[8] Proxy (${ANTHROPIC_BASE_URL:-http://localhost:8082})"
PROXY_URL="${ANTHROPIC_BASE_URL:-http://localhost:8082}"
PROXY_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${PROXY_URL}/health" 2>/dev/null || echo "000")
if [ "$PROXY_CODE" != "000" ]; then
  check "proxy reachable" "ok" "HTTP $PROXY_CODE"
else
  check "proxy reachable" "fail" "connection refused"
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
