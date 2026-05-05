#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "══════════════════════════════════════════════"
echo "  remote-claude-openclaw — install"
echo "══════════════════════════════════════════════"
echo ""

fail() { echo "  FAIL: $1"; exit 1; }
ok()   { echo "  OK:   $1"; }

# ── 1. Check prerequisites ────────────────────
echo "[1/6] Checking prerequisites..."
command -v node   >/dev/null 2>&1 && ok "node $(node --version)"   || fail "node not found"
command -v python3 >/dev/null 2>&1 && ok "python3 $(python3 --version 2>&1 | cut -d' ' -f2)" || fail "python3 not found"
command -v git     >/dev/null 2>&1 && ok "git $(git --version | cut -d' ' -f3)" || fail "git not found"

# ── 2. Check OpenClaw ─────────────────────────
echo ""
echo "[2/6] Checking OpenClaw..."
if command -v openclaw >/dev/null 2>&1; then
  OC_VERSION=$(openclaw --version 2>&1 | head -1)
  ok "openclaw: $OC_VERSION"
else
  fail "openclaw not found — install from https://docs.openclaw.ai"
fi

# ── 3. Check Claude Code ──────────────────────
echo ""
echo "[3/6] Checking Claude Code..."
if command -v claude >/dev/null 2>&1; then
  ok "claude CLI found at $(command -v claude)"
else
  fail "claude CLI not found — install via: npm install -g @anthropic-ai/claude-code"
fi

# ── 4. Check .env ─────────────────────────────
echo ""
echo "[4/6] Checking .env..."
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

# ── 5. Install safety rules to OpenClaw workspace ──
echo ""
echo "[5/6] Installing safety rules to OpenClaw workspace..."
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
mkdir -p "$WORKSPACE"
if [ -f "$ROOT_DIR/skills/remote-claude-code/CLAUDE.md" ]; then
  cp "$ROOT_DIR/skills/remote-claude-code/CLAUDE.md" "$WORKSPACE/CLAUDE.md"
  ok "CLAUDE.md installed to $WORKSPACE"
else
  echo "  WARN: skills/remote-claude-code/CLAUDE.md not found"
fi

# ── 6. Check repo ─────────────────────────────
echo ""
echo "[6/6] Checking repo at ${LOCAL_REPO_PATH:-NOT_SET}..."
if [ -d "${LOCAL_REPO_PATH:-}" ]; then
  ok "repo exists at $LOCAL_REPO_PATH"
  if [ -d "$LOCAL_REPO_PATH/.git" ]; then
    ok "  -> is a git repository"
  else
    echo "  WARN: not a git repository"
  fi
else
  fail "repo not found — check LOCAL_REPO_PATH in .env"
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
