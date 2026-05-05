# Architecture — remote-claude-openclaw

## Problem

Two founders (Siddharth/CTO, Hayagreev/CEO) need to control their own laptops from their own phones using Claude Code. Each laptop runs its own agent. Nothing routes through a central server.

## Design

```
┌─────────────────────────────┐    ┌─────────────────────────────┐
│    Siddharth's Laptop       │    │    Hayagreev's Laptop       │
│                             │    │                             │
│  .env: FOUNDER_ID=siddharth │    │  .env: FOUNDER_ID=hayagreev │
│  LOCAL_REPO_PATH=...Shanthi │    │  LOCAL_REPO_PATH=...Shanthi │
│                             │    │                             │
│  ┌─────────────────┐        │    │  ┌─────────────────┐        │
│  │  OpenClaw Bridge │        │    │  │  OpenClaw Bridge │        │
│  │  (WhatsApp/TG)  │        │    │  │  (WhatsApp/TG)  │        │
│  └───────┬─────────┘        │    │  └───────┬─────────┘        │
│          │                  │    │          │                  │
│  ┌───────▼─────────┐        │    │  ┌───────▼─────────┐        │
│  │  remote-claude- │        │    │  │  remote-claude- │        │
│  │  code agent.py  │        │    │  │  code agent.py  │        │
│  └───────┬─────────┘        │    │  └───────┬─────────┘        │
│          │                  │    │          │                  │
│  ┌───────▼─────────┐        │    │  ┌───────▼─────────┐        │
│  │  Claude Code    │        │    │  │  Claude Code    │        │
│  │  CLI            │        │    │  │  CLI            │        │
│  └───────┬─────────┘        │    │  └───────┬─────────┘        │
│          │                  │    │          │                  │
│  ┌───────▼─────────┐        │    │  ┌───────▼─────────┐        │
│  │  ANTHROPIC_PROXY│        │    │  │  ANTHROPIC_PROXY│        │
│  │  localhost:8082 │        │    │  │  localhost:8082 │        │
│  └───────┬─────────┘        │    │  └───────┬─────────┘        │
│          │                  │    │          │                  │
│  ┌───────▼─────────┐        │    │  ┌───────▼─────────┐        │
│  │  DeepSeek/      │        │    │  │  DeepSeek/      │        │
│  │  NVIDIA NIM     │        │    │  │  NVIDIA NIM     │        │
│  └─────────────────┘        │    │  └─────────────────┘        │
│                             │    │                             │
└─────────────────────────────┘    └─────────────────────────────┘
         ▲                                  ▲
         │ WhatsApp/Telegram/Slack          │ WhatsApp/Telegram/Slack
         │                                  │
    ┌────┴────┐                        ┌────┴────┐
    │Siddharth│                        │Hayagreev│
    │  Phone  │                        │  Phone  │
    └─────────┘                        └─────────┘
```

## Key Principles

### 1. No Central Server
Each laptop runs independently. No laptop routes tasks to another laptop.

### 2. Per-Laptop Identity
The `.env` file on each laptop defines who owns it. The agent serves exactly one founder.

### 3. Phone → Laptop → Phone
Messages flow: Phone → Channel → Agent → Claude Code → LOCAL_REPO_PATH → Response → Same Phone.

### 4. Model Aliases, Not Model Names
Business logic uses Claude aliases (`opus`, `sonnet`, `haiku`). The local proxy maps these to real models. This means the agent code never hardcodes a provider name.

### 5. Safety by Default
- No push without explicit "push" command
- No file deletion without confirmation
- No operations outside LOCAL_REPO_PATH
- Unknown senders rejected
- Every shell command logged

## File Map

```
remote-claude-openclaw/
├── .env.example              # Template — copy to .env per laptop
├── .env                      # NOT in git — per-laptop secrets
├── config/
│   ├── founders.example.json # Known founders & channel IDs
│   ├── founders.json         # Local copy (gitignored)
│   ├── agent.example.json    # Agent runtime config
│   └── agent.json            # Local copy (gitignored)
├── scripts/
│   ├── install.sh            # Idempotent setup
│   ├── doctor.sh             # Diagnostic checks
│   ├── start.sh              # Launch agent
│   └── stop.sh               # Graceful shutdown
├── skills/
│   └── remote-claude-code/
│       └── agent.py          # Core agent (channel bridge + CC runner)
├── docs/
│   ├── ARCHITECTURE.md       # This file
│   ├── SETUP_CEO.md          # CEO quickstart
│   └── SAFETY.md             # Safety rules
├── tests/
│   └── test_harness.py       # Integration tests
└── README.md
```

## Message Flow

```
1. Founder sends "fix: login bug" via WhatsApp
2. Twilio webhook → ChannelBridge.receive_message()
3. Agent verifies sender ∈ ALLOWED_SENDERS
4. Agent resolves: this is Siddharth's laptop → Siddharth's repo
5. Agent calls: claude --print "Fix login bug. Edit locally. Run tests. No push."
6. Claude Code operates on LOCAL_REPO_PATH
7. Agent sends response back to Siddharth's phone via WhatsApp
```

## Adding a Channel

1. Implement `ChannelBridge` subclass for the channel
2. Add credentials to `.env`
3. Set `CHANNEL=whatsapp|telegram|slack`

Current implementation: stdin/stdout stub (for testing).
Production: swap in OpenClaw or direct API integration.
