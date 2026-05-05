# remote-claude-openclaw

Phone-controlled Claude Code agent for multi-founder local development.

Each founder runs their own agent on their own laptop. Their phone controls only their laptop. No central server.

## What this is

A portable Git repo that gives both founders (CTO and CEO) the ability to send commands from their phones and have Claude Code execute them on their own laptops — safely.

```
Phone: "fix: login bug"
  → WhatsApp/Telegram/Slack
    → Local agent (your laptop only)
      → Claude Code (your repo only)
        → Response back to your phone
```

## Quickstart — Siddharth (CTO)

```bash
cd ~/Projects
git clone <repo-url> remote-claude-openclaw
cd remote-claude-openclaw
cp .env.example .env
# Edit .env → FOUNDER_ID=siddharth, FOUNDER_ROLE=CTO
chmod +x scripts/*.sh
./scripts/install.sh
./scripts/doctor.sh
./scripts/start.sh
```

## Quickstart — Hayagreev (CEO)

```bash
cd ~/Projects
git clone <repo-url> remote-claude-openclaw
cd remote-claude-openclaw
cp .env.example .env
# Edit .env → FOUNDER_ID=hayagreev, FOUNDER_ROLE=CEO
# Set LOCAL_REPO_PATH to your copy of the repo
chmod +x scripts/*.sh
./scripts/install.sh
./scripts/doctor.sh
./scripts/start.sh
```

See [docs/SETUP_CEO.md](docs/SETUP_CEO.md) for detailed CEO instructions.

## Configure .env

Each laptop needs its own `.env`:

```bash
# Who owns THIS laptop
FOUNDER_ID=siddharth
FOUNDER_NAME=Siddharth
FOUNDER_ROLE=CTO

# Where the code lives on THIS laptop
LOCAL_REPO_PATH=/Users/siddharthsaminathan/Projects/Shanthibeta2

# Claude Code CLI
CLAUDE_CODE_COMMAND=claude

# Proxy (maps Claude aliases → real models)
ANTHROPIC_BASE_URL=http://localhost:8082
ANTHROPIC_AUTH_TOKEN=your-proxy-token
MAIN_MODEL_ALIAS=opus
CHEAP_MODEL_ALIAS=haiku

# Channel: whatsapp, telegram, or slack
CHANNEL=whatsapp

# Who can send commands to THIS laptop
ALLOWED_SENDERS=+919XXXXXXXXX
```

## Connect WhatsApp / Telegram / Slack

### WhatsApp (via Twilio)
1. Set up a Twilio account and WhatsApp Sandbox
2. Set `CHANNEL=whatsapp`
3. Add `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to `.env`

### Telegram
1. Create a bot via @BotFather
2. Set `CHANNEL=telegram`
3. Add `TELEGRAM_BOT_TOKEN` to `.env`

### Slack
1. Create a Slack App with Socket Mode
2. Set `CHANNEL=slack`
3. Add `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` to `.env`

## Commands (send from phone)

| Command | Example | What happens |
|---------|---------|-------------|
| `plan: <task>` | `plan: refactor auth middleware` | Claude plans, no edits |
| `fix: <task>` | `fix: login returns 500 on null email` | Edits locally, runs tests, no push |
| `status` | `status` | Shows branch, last commit, dirty files |
| `diff` | `diff` | Summarizes uncommitted changes |
| `commit: <msg>` | `commit: fix null email crash` | Commits local diff |
| `push` | `push` | Pushes to remote |
| `stop` | `stop` | Kills current Claude run |

## Safety rules

See [docs/SAFETY.md](docs/SAFETY.md) for full details.

- Never pushes without explicit `push` command
- Never deletes files without confirmation
- Never runs destructive commands (`rm -rf`, `git reset --hard`, etc.)
- Never operates outside `LOCAL_REPO_PATH`
- Unknown senders are rejected
- Every shell command is logged to `logs/commands-*.log`

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

Key principles:
- Each laptop is independent — no central server
- `.env` defines who owns THIS laptop
- Siddharth's phone → Siddharth's laptop only
- Hayagreev's phone → Hayagreev's laptop only
- Model aliases only (opus/sonnet/haiku) — proxy maps to real models
- No provider names hardcoded in business logic

## Testing

```bash
python3 tests/test_harness.py
```

Tests verify:
1. Siddharth config → Siddharth repo
2. CEO config → CEO repo
3. Unknown sender rejected
4. fix command does not push
5. push requires explicit approval
6. Operation outside LOCAL_REPO_PATH refused

## Files

```
remote-claude-openclaw/
├── .env.example              # Template (git tracked)
├── config/
│   ├── founders.example.json # Known founders
│   └── agent.example.json    # Agent runtime config
├── scripts/
│   ├── install.sh            # Idempotent setup
│   ├── doctor.sh             # Health check
│   ├── start.sh              # Launch agent
│   └── stop.sh               # Graceful shutdown
├── skills/
│   └── remote-claude-code/
│       └── agent.py          # Core agent
├── docs/
│   ├── ARCHITECTURE.md       # Full design
│   ├── SETUP_CEO.md          # CEO quickstart
│   └── SAFETY.md             # Safety rules
└── tests/
    └── test_harness.py       # Integration tests
```
