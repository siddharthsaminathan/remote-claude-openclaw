# Architecture — remote-claude-openclaw

## Design

```
┌──────────────────────────────────────────┐
│         Siddharth's Laptop               │
│                                          │
│  WhatsApp Message from Siddharth's Phone │
│          │                               │
│  ┌───────▼──────────────────────┐        │
│  │  OpenClaw Gateway            │        │
│  │  - Port 18789 (local)        │        │
│  │  - WhatsApp plugin enabled   │        │
│  │  - Allowlist: +917299707403  │        │
│  │  - Transport layer ONLY      │        │
│  └───────┬──────────────────────┘        │
│          │                               │
│  ┌───────▼──────────────────────┐        │
│  │  Agent Session               │        │
│  │  - Reads workspace CLAUDE.md │        │
│  │  - Enforces safety rules     │        │
│  │  - Routes commands           │        │
│  └───────┬──────────────────────┘        │
│          │                               │
│  ┌───────▼──────────────────────┐        │
│  │  Claude Code CLI             │        │
│  │  - Uses local proxy :8082    │        │
│  │  - Operates on Shanthibeta2  │        │
│  └───────┬──────────────────────┘        │
│          │                               │
│  ┌───────▼──────────────────────┐        │
│  │  Local Proxy (:8082)         │        │
│  │  - opus → deepseek-v4-pro    │        │
│  │  - haiku → deepseek-v4-flash │        │
│  └──────────────────────────────┘        │
│                                          │
│  Response → OpenClaw → WhatsApp → Phone  │
└──────────────────────────────────────────┘

  (Same architecture on Hayagreev's laptop,
   different .env, different repo path)
```

## Key Principles

### 1. OpenClaw = Transport Only
OpenClaw handles WhatsApp message receipt and reply delivery. It does NOT make AI decisions or run code. The agent session (informed by workspace CLAUDE.md) and Claude Code CLI handle all logic.

### 2. Safety in CLAUDE.md
The workspace CLAUDE.md is the canonical safety rule source. It's installed by `install.sh` from `skills/remote-claude-code/CLAUDE.md`. Every agent session reads it on startup.

### 3. Claude Code = Execution
Heavy code work (planning, fixing) is delegated to Claude Code CLI which uses the local Anthropic proxy. Lightweight operations (status, diff) run shell commands directly.

### 4. Per-Laptop Identity
Each laptop has its own `.env` defining FOUNDER_ID, LOCAL_REPO_PATH, and ALLOWED_SENDERS. There is zero cross-laptop routing.

### 5. Model Aliases
Business logic uses Claude aliases (opus, sonnet, haiku). The local proxy at `localhost:8082` maps these to real models. No provider names are hardcoded.

## File Roles

| File | Role |
|------|------|
| `~/.openclaw/openclaw.json` | OpenClaw config: WhatsApp channel, gateway port, auth |
| `~/.openclaw/workspace/CLAUDE.md` | Safety rules + command reference (installed by install.sh) |
| `~/.openclaw/workspace/AGENTS.md` | Agent startup sequence (reads CLAUDE.md) |
| `~/.openclaw/workspace/USER.md` | Owner identity, repo path, preferences |
| `remote-claude-openclaw/.env` | Per-laptop: FOUNDER_ID, repo path, proxy URL |
| `remote-claude-openclaw/skills/remote-claude-code/CLAUDE.md` | Canonical safety rule source |
| `remote-claude-openclaw/skills/remote-claude-code/agent.py` | Reference implementation + test harness |

## Message Flow

```
1. Siddharth sends "fix: login bug" via WhatsApp
2. OpenClaw WhatsApp plugin receives the message
3. OpenClaw verifies sender ∈ allowFrom [+917299707403]
4. Agent session starts, reads CLAUDE.md (safety rules)
5. Agent recognizes "fix:" command
6. Agent invokes: claude --print "Fix login bug. Edit locally. No push."
7. Claude Code operates on /Users/siddharthsaminathan/Projects/Shanthibeta2
8. Claude Code returns result
9. Agent formats response for WhatsApp
10. OpenClaw sends reply via WhatsApp to Siddharth's phone
```

## Startup

```bash
./scripts/start.sh
# → Starts OpenClaw gateway on port 18789
# → Gateway connects WhatsApp plugin
# → Agent sessions read CLAUDE.md on each message
# → Safety rules enforced on every command
```
